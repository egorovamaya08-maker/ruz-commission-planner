import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="RUZ Commission Planner",
    page_icon="📅",
    layout="wide"
)

st.title("📅 RUZ Commission Planner")
st.markdown("**Планирование комиссий и поиск свободных окон • СПбГТУ**")

# Подключение к Supabase
@st.cache_resource
def init_supabase():
    try:
        conn = st.connection("supabase", type="sql")
        st.success("✅ Подключено к Supabase")
        return conn
    except Exception as e:
        st.error(f"❌ Ошибка подключения к базе: {e}")
        st.info("Проверьте secrets в Streamlit Cloud")
        return None

supabase = init_supabase()

# ====================== ИНТЕРФЕЙС ======================
with st.sidebar:
    st.header("Настройки")
    st.caption("Приватное приложение")

    if st.button("🔄 Полностью обновить расписание", type="primary"):
        if supabase:
            st.info("Парсер расписания будет добавлен на следующем этапе")
        else:
            st.error("Сначала подключите Supabase")

# Вкладки
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Обновление данных", 
    "Поиск свободных окон", 
    "Планирование комиссий", 
    "Статистика нагрузки", 
    "Сохранённые варианты"
])

with tab1:
    st.subheader("Обновление расписания")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))
    
    st.info("✅ Supabase подключён. Парсер добавим дальше.")

with tab2:
    st.subheader("Поиск свободных окон")
    st.info("Фильтры и поиск появятся на следующих этапах.")

with tab3:
    st.subheader("Планирование комиссий")
    st.info("Здесь будет выбор преподавателей и генерация вариантов.")

with tab4:
    st.subheader("Статистика нагрузки")
    st.info("Статистика по дисциплинам и преподавателям.")

with tab5:
    st.subheader("Сохранённые варианты комиссий")
    st.info("Список сохранённых комиссий.")

st.caption("RUZ Commission Planner v0.1 • Данные в Supabase")
