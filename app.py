import streamlit as st

st.set_page_config(page_title="Claude Manager", page_icon="🤖", layout="wide")

st.title("Claude Manager")
st.write("Welcome! This is the starting point for the app.")

with st.sidebar:
    st.header("Settings")
    name = st.text_input("Your name", value="")

if name:
    st.success(f"Hello, {name}!")
