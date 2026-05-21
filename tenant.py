"""
tenant.py — Tenant context helpers.
A tenant = a Factory. Every operational call must run with a factory_id in
session_state so that all database queries are auto-filtered.
"""
from typing import Optional


def current_factory_id() -> Optional[int]:
    """Returns the current logged-in user's factory_id, or None."""
    try:
        import streamlit as st
        return st.session_state.get('current_factory_id')
    except Exception:
        return None


def current_factory_code() -> str:
    try:
        import streamlit as st
        return st.session_state.get('current_factory_code', '') or ''
    except Exception:
        return ''


def current_factory_name() -> str:
    try:
        import streamlit as st
        lang = st.session_state.get('lang', 'ar')
        if lang == 'en':
            n = st.session_state.get('current_factory_name_en', '')
            if n:
                return n
        return st.session_state.get('current_factory_name', '') or 'Smart Factory'
    except Exception:
        return 'Smart Factory'


def require_factory() -> bool:
    """Returns True if a factory is bound to the session."""
    return current_factory_id() is not None


def set_factory_in_session(user_dict: dict) -> None:
    """Called by auth.py after a successful login / signup."""
    try:
        import streamlit as st
        st.session_state['current_factory_id']      = user_dict.get('factory_id')
        st.session_state['current_factory_code']    = user_dict.get('factory_code', '')
        st.session_state['current_factory_name']    = user_dict.get('factory_name', '')
        st.session_state['current_factory_name_en'] = user_dict.get('factory_name_en', '')
        st.session_state['current_factory_logo']    = user_dict.get('factory_logo', '')
    except Exception:
        pass


def clear_factory_from_session() -> None:
    try:
        import streamlit as st
        for k in (
            'current_factory_id', 'current_factory_code',
            'current_factory_name', 'current_factory_name_en',
            'current_factory_logo'
        ):
            if k in st.session_state:
                st.session_state[k] = None
    except Exception:
        pass
