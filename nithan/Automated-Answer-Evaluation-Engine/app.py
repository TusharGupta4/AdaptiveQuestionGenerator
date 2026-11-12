import streamlit as st

from app_views.custom_eval_view import render_custom_evaluation_mode
from app_views.evaluation_view import render_evaluation
from app_views.question_bank_view import (
    ALL_QUESTIONS,
    build_question_text_map,
    render_question_bank_mode,
)

NAVIGATION = {
    "Question Bank Mode": render_question_bank_mode,
    "Custom Evaluation (Ad-Hoc Testing)": render_custom_evaluation_mode,
}

__all__ = ['ALL_QUESTIONS', 'build_question_text_map', 'render_evaluation']


def configure_page() -> None:
    st.set_page_config(
        page_title="OCR Answer Sheet Evaluator",
        layout="wide",
    )
    st.title("AI-Powered Answer Sheet Evaluation System")
    st.markdown("---")


def main() -> None:
    configure_page()
    with st.sidebar:
        st.header("Navigation")
        mode = st.radio("Mode", tuple(NAVIGATION), key="app_navigation_mode")
    NAVIGATION[mode]()


if __name__ == '__main__':
    main()
