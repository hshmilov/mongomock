import uuid
from datetime import datetime, timedelta

from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

# This is mostly copied from the internet so don't CR too much


class DBSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=True):
        def on_update(this):
            this.modified = True

        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class CachedSessionInterface(SessionInterface):
    session_class = DBSession

    def __init__(self, all_sessions):
        self.__data = all_sessions

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if not sid:
            sid = self.__generate_sid()
            return self.session_class(sid=sid)

        doc = self.__data.get(sid)
        # Check if exists and not expired.
        if doc and doc['exp'].replace(tzinfo=None) > datetime.utcnow():
            session = doc['d']
        else:
            # If the SID doesn't exist - create a new one to avoid possibility
            # of user-generated SID with invalid format (e.g. "abc123").
            sid = self.__generate_sid()
            session = self.session_class(sid=sid)
        return session

    def save_session(self, app, session, response):
        cookie_exp = self.get_expiration_time(app, session)

        if not session:
            self.__data.pop(session.sid, None)
            if session:
                response.delete_cookie(key=app.session_cookie_name)
            return

        # If session isn't permanent if will be considered valid for 1 day
        # (but not cookie which will be deleted by browser after exit).
        session_exp = cookie_exp or datetime.utcnow() + timedelta(days=1)
        self.__data[session.sid] = {
            'd': session,
            'exp': session_exp,
        }
        response.set_cookie(key=app.session_cookie_name,
                            value=session.sid,
                            expires=cookie_exp,
                            secure=self.get_cookie_secure(app),
                            httponly=self.get_cookie_httponly(app))

    @staticmethod
    def __generate_sid():
        return uuid.uuid4().hex
