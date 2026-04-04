import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="RUZ Commission Planner", layout="wide")

st.title("📅 RUZ Commission Planner")
st.markdown("**Планирование**")

st.sidebar.success("✅ Приложение запущено")

tab1, tab2, tab3, tab4 = st.tabs([
    "Обновление расписания", 
    "Поиск свободных окон", 
    "Планирование комиссий", 
    "Статистика"
])

with tab1:
    st.subheader("Загрузка расписания")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Начало", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Конец", datetime(2026, 5, 25))
    
    group = st.text_input("Номер группы", "3530902/20101")
    
    if st.button("Запустить парсинг"):
        st.info("🔧 Парсер будет добавлен на следующем этапе. Пока приложение работает.")
        st.success("Приложение успешно запущено!")

with tab2:
    st.subheader("Поиск свободных окон")
    st.info("Функция будет доступна после добавления данных.")

with tab3:
    st.subheader("Планирование комиссий")
    st.info("Здесь будет форма для создания комиссий.")

with tab4:
    st.subheader("Статистика")
    st.info("Статистика появится после добавления расписания.")

st.caption("Упрощённая версия • Работает без Supabase")
