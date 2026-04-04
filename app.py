import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Commission Planner")
st.markdown("**Планирование комиссий • СПбГТУ**")

# Подключение к Supabase через встроенный connector
@st.cache_resource
def get_db():
    try:
        db = st.connection("supabase", type="sql")
        st.sidebar.success("✅ Supabase подключён")
        return db
    except Exception as e:
        st.sidebar.error(f"Ошибка подключения: {e}")
        return None

db = get_db()

# Основные вкладки
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
        st.info("Парсер будет добавлен на следующем шаге. Пока показываем заглушку.")
        st.write("Группа:", group, "Период:", start_date, "-", end_date)

with tab2:
    st.subheader("Поиск свободных окон")
    st.info("Функция поиска будет доступна после добавления данных в базу.")

with tab3:
    st.subheader("Планирование комиссий")
    st.info("Здесь будет выбор преподавателей и генерация вариантов.")

with tab4:
    st.subheader("Статистика")
    if db:
        st.info("Подключение к базе работает. Статистика появится позже.")
    else:
        st.warning("База не подключена")

st.caption("Версия упрощённая • Для стабильного деплоя")
