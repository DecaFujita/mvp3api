from collections import defaultdict
from typing import Dict, List

from flask_openapi3 import OpenAPI, Info, Tag
from flask import redirect, request, make_response
from sqlalchemy.exc import IntegrityError

from model import Session, SessionLocal, Provider, Activity, ProviderActivity
from logger import logger
from schemas import *

info = Info(
    title="TrakClub API",
    version="1.0.0",
    description="MVP API for clubs (providers), activity types, and scheduled sessions.",
)
app = OpenAPI(__name__, info=info)


def _apply_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
    )
    req_headers = request.headers.get("Access-Control-Request-Headers")
    if req_headers:
        response.headers["Access-Control-Allow-Headers"] = req_headers
    else:
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, Accept, X-Requested-With"
        )
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


@app.before_request
def _cors_preflight():
    if request.method == "OPTIONS":
        return _apply_cors_headers(make_response("", 204))


@app.after_request
def _cors_after(response):
    return _apply_cors_headers(response)


home_tag = Tag(name="Docs", description="API Documentation")
provider_tag = Tag(name="Provider", description="Manage clubs")
activity_tag = Tag(name="Activity", description="Manage activities")
session_tag = Tag(name="Session", description="Manage scheduled sessions")


@app.get("/", tags=[home_tag], summary="Open API documentation (redirect)")
def home():
    return redirect("/openapi")


@app.post(
    "/provider",
    tags=[provider_tag],
    summary="Create a club (provider)",
    responses={"200": ProviderViewSchema, "409": ErrorSchema, "400": ErrorSchema},
)
def add_provider(form: ProviderSchema):
    try:
        provider = Provider(
            name=form.name,
            address=form.address,
            city=form.city,
            state=form.state,
            phone=form.phone,
            email=form.email,
            instagram=form.instagram,
            description=form.description,
        )

        session = SessionLocal()
        session.add(provider)
        session.commit()

        logger.debug(f"Created provider: {provider.name}")

        return present_provider(provider, []), 200

    except IntegrityError:
        logger.warning("Provider already exists")
        return {"message": "Provider already exists"}, 409

    except Exception as e:
        logger.warning(f"Error creating provider: {e}")
        return {"message": "Could not create provider"}, 400


def _activities_by_provider_ids(
    sa_session, provider_ids: List[int]
) -> Dict[int, List[Activity]]:
    if not provider_ids:
        return {}
    by_pid: Dict[int, dict] = defaultdict(lambda: {"order": [], "ids": set()})

    def _add(pid: int, act: Activity) -> None:
        bucket = by_pid[pid]
        if act.id not in bucket["ids"]:
            bucket["ids"].add(act.id)
            bucket["order"].append(act)

    for pid, act in (
        sa_session.query(Session.provider_id, Activity)
        .join(Activity, Session.activity_id == Activity.id)
        .filter(Session.provider_id.in_(provider_ids))
        .all()
    ):
        _add(pid, act)

    for pa, act in (
        sa_session.query(ProviderActivity, Activity)
        .join(Activity, ProviderActivity.activity_id == Activity.id)
        .filter(ProviderActivity.provider_id.in_(provider_ids))
        .all()
    ):
        _add(pa.provider_id, act)

    return {pid: data["order"] for pid, data in by_pid.items()}


@app.get(
    "/providers",
    tags=[provider_tag],
    summary="List all clubs (providers)",
    responses={"200": ProviderListSchema},
)
def get_providers():
    session = SessionLocal()
    providers = session.query(Provider).all()
    ids = [p.id for p in providers]
    activities_by_provider = _activities_by_provider_ids(session, ids)

    return present_providers(providers, activities_by_provider), 200


@app.get(
    "/provider/<int:provider_id>",
    tags=[provider_tag],
    summary="Get one club by id (full detail)",
    responses={"200": ProviderDetailViewSchema, "404": ErrorSchema},
)
def get_provider_by_id(path: ProviderIdPath):
    session = SessionLocal()
    provider = session.query(Provider).filter(Provider.id == path.provider_id).first()

    if not provider:
        logger.warning("Provider not found")
        return {"message": "Provider not found"}, 404

    activities = _activities_by_provider_ids(session, [path.provider_id]).get(
        path.provider_id, []
    )
    return present_provider_details(provider, activities), 200


@app.put(
    "/provider/<int:provider_id>",
    tags=[provider_tag],
    summary="Update a club (provider)",
    responses={"200": ProviderDetailViewSchema, "404": ErrorSchema, "400": ErrorSchema},
)
def update_provider_by_id(path: ProviderIdPath, form: ProviderSchema):
    db = SessionLocal()
    provider = db.get(Provider, path.provider_id)
    if not provider:
        logger.warning("Provider not found")
        return {"message": "Provider not found"}, 404

    try:
        provider.name = form.name
        provider.address = form.address
        provider.city = form.city
        provider.state = form.state
        provider.phone = form.phone
        provider.email = form.email
        provider.instagram = form.instagram
        provider.description = form.description
        db.commit()

        activities = _activities_by_provider_ids(db, [provider.id]).get(provider.id, [])
        logger.debug(f"Updated provider id={provider.id}")
        return present_provider_details(provider, activities), 200
    except IntegrityError:
        db.rollback()
        logger.warning("Provider update conflicts with an existing record")
        return {"message": "Could not update provider"}, 400
    except Exception as e:
        db.rollback()
        logger.warning(f"Error updating provider: {e}")
        return {"message": "Could not update provider"}, 400


@app.delete(
    "/provider/<int:provider_id>",
    tags=[provider_tag],
    summary="Delete a club (provider)",
    responses={"200": ProviderDeleteSchema, "404": ErrorSchema, "409": ErrorSchema},
)
def delete_provider_by_id(path: ProviderIdPath):
    db = SessionLocal()
    provider = db.get(Provider, path.provider_id)
    if not provider:
        logger.warning("Provider not found")
        return {"message": "Provider not found"}, 404
    try:
        db.query(Session).filter(Session.provider_id == path.provider_id).delete(
            synchronize_session=False
        )
        db.query(ProviderActivity).filter(
            ProviderActivity.provider_id == path.provider_id
        ).delete(synchronize_session=False)
        db.delete(provider)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Provider delete blocked by existing references")
        return {
            "message": "Cannot delete provider: remove or reassign dependent sessions first",
        }, 409
    logger.debug(f"Deleted provider id={path.provider_id}")
    return {"message": "Provider deleted", "id": path.provider_id}, 200


@app.post(
    "/activity",
    tags=[activity_tag],
    summary="Create an activity type",
    responses={"200": ActivityViewSchema, "409": ErrorSchema, "400": ErrorSchema},
)
def add_activity(form: ActivitySchema):
    try:
        activity = Activity(name=form.name)

        session = SessionLocal()
        session.add(activity)
        session.commit()

        logger.debug(f"Created activity: {activity.name}")

        return {"id": activity.id, "name": activity.name}, 200

    except IntegrityError:
        logger.warning("Activity already exists")
        return {"message": "Activity already exists"}, 409

    except Exception as e:
        logger.warning(f"Error creating activity: {e}")
        return {"message": "Could not create activity"}, 400


@app.get(
    "/activities",
    tags=[activity_tag],
    summary="List all activity types",
    responses={"200": ActivityListSchema},
)
def get_activities():
    session = SessionLocal()
    activities = session.query(Activity).all()

    return present_activities(activities), 200


@app.get(
    "/activity/<int:activity_id>",
    tags=[activity_tag],
    summary="Get one activity by id",
    responses={"200": ActivityViewSchema, "404": ErrorSchema},
)
def get_activity_by_id(path: ActivityIdPath):
    session = SessionLocal()
    activity = session.query(Activity).filter(Activity.id == path.activity_id).first()

    if not activity:
        logger.warning("Activity not found")
        return {"message": "Activity not found"}, 404

    return {"id": activity.id, "name": activity.name}, 200


@app.delete(
    "/activity/<int:activity_id>",
    tags=[activity_tag],
    summary="Delete an activity type",
    responses={"200": ActivityDeleteSchema, "404": ErrorSchema, "409": ErrorSchema},
)
def delete_activity_by_id(path: ActivityIdPath):
    db = SessionLocal()
    activity = db.get(Activity, path.activity_id)
    if not activity:
        logger.warning("Activity not found")
        return {"message": "Activity not found"}, 404
    try:
        db.delete(activity)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Activity delete blocked by existing references")
        return {
            "message": "Cannot delete activity: remove sessions that use this activity first",
        }, 409
    logger.debug(f"Deleted activity id={path.activity_id}")
    return {"message": "Activity deleted", "id": path.activity_id}, 200


@app.post(
    "/session",
    tags=[session_tag],
    summary="Schedule a session (provider + activity + time)",
    responses={"200": SessionViewSchema, "400": ErrorSchema, "409": ErrorSchema},
)
def add_session(form: SessionSchema):
    try:
        new_session = Session(
            weekday=form.weekday,
            time=form.time,
            provider_id=form.provider_id,
            activity_id=form.activity_id,
        )

        db = SessionLocal()
        db.add(new_session)
        db.commit()

        logger.debug(f"Created session: {form.weekday} {form.time}")

        return present_session(new_session), 200

    except IntegrityError:
        logger.warning("Session FK conflict on create")
        return {"message": "Invalid provider_id or activity_id (or duplicate row)"}, 409

    except Exception as e:
        logger.warning(f"Error creating session: {e}")
        return {"message": "Could not create session"}, 400


@app.get(
    "/sessions",
    tags=[session_tag],
    summary="List all scheduled sessions",
    responses={"200": SessionListSchema},
)
def get_sessions():
    db = SessionLocal()
    rows = db.query(Session).all()

    return present_sessions(rows), 200


@app.get(
    "/session/<int:session_id>",
    tags=[session_tag],
    summary="Get one scheduled session by id",
    responses={"200": SessionViewSchema, "404": ErrorSchema},
)
def get_session_by_id(path: SessionIdPath):
    db = SessionLocal()

    row = db.query(Session).filter(Session.id == path.session_id).first()

    if not row:
        logger.warning("Session not found")
        return {"message": "Session not found"}, 404

    return present_session(row), 200


@app.put(
    "/session/<int:session_id>",
    tags=[session_tag],
    summary="Update a scheduled session",
    responses={"200": SessionViewSchema, "404": ErrorSchema, "400": ErrorSchema, "409": ErrorSchema},
)
def update_session_by_id(path: SessionIdPath, form: SessionSchema):
    db = SessionLocal()
    row = db.get(Session, path.session_id)
    if not row:
        logger.warning("Session not found")
        return {"message": "Session not found"}, 404

    try:
        row.weekday = form.weekday
        row.time = form.time
        row.provider_id = form.provider_id
        row.activity_id = form.activity_id
        db.commit()
        logger.debug(f"Updated session id={row.id}")
        return present_session(row), 200
    except IntegrityError:
        db.rollback()
        logger.warning("Session update conflicts with an existing row")
        return {"message": "Invalid provider_id or activity_id (or duplicate row)"}, 409
    except Exception as e:
        db.rollback()
        logger.warning(f"Error updating session: {e}")
        return {"message": "Could not update session"}, 400


@app.delete(
    "/session/<int:session_id>",
    tags=[session_tag],
    summary="Delete a scheduled session",
    responses={"200": SessionDeleteSchema, "404": ErrorSchema},
)
def delete_session_by_id(path: SessionIdPath):
    db = SessionLocal()
    row = db.get(Session, path.session_id)
    if not row:
        logger.warning("Session not found")
        return {"message": "Session not found"}, 404
    db.delete(row)
    db.commit()
    logger.debug(f"Deleted session id={path.session_id}")
    return {"message": "Session deleted", "id": path.session_id}, 200
