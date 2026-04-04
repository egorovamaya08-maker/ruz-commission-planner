import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")
st.markdown("**Планирование**")

# ====================== ПАРСЕР (на основе твоих старых скриптов) ======================
def parse_schedule(group_id: str, start_date: datetime, end_date: datetime):
    """Простая версия парсера расписания"""
    lessons = []
    try:
        # Генерируем понедельники
        current = start_date - timedelta(days=start_date.weekday())
        while current <= end_date:
            url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                st.warning(f"Ошибка при загрузке недели {current.strftime('%Y-%m-%d')}")
                current += timedelta(weeks=1)
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Здесь будет полноценный парсинг (пока заглушка)
            lessons.append({
                "date": current.strftime("%Y-%m-%d"),
                "group": group_id,
                "subject": "Заглушка дисциплины",
                "type": "Лекция",
                "teacher": "Иванов И.И.",
                "time_start": "10:00",
                "time_end": "11:30"
            })
            
            current += timedelta(weeks=1)
            time.sleep(8)  # пауза, чтобы не нагружать сайт ruz
            
        return pd.DataFrame(lessons)
        
    except Exception as e:
        st.error(f"Ошибка парсинга: {e}")
        return pd.DataFrame()

# ====================== ОСНОВНОЙ ИНТЕРФЕЙС ======================
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Обновление расписания", 
    "🔍 Поиск свободных окон", 
    "📅 Планирование комиссий", 
    "📊 Статистика"
])

with tab1:
    st.subheader("Загрузка расписания из RUZ")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))
    
    group_id = st.text_input("Номер группы", "3530902/20101", help="Пример: 3530902/20101")
    
    if st.button("🚀 Запустить парсинг расписания", type="primary"):
        with st.spinner("Парсинг расписания... (это может занять время)"):
            df = parse_schedule(group_id, start_date, end_date)
            
            if not df.empty:
                st.success(f"Успешно загружено {len(df)} занятий!")
                st.dataframe(df)
                
                # Сохраняем в session_state для других вкладок
                st.session_state.schedule_df = df
            else:
                st.error("Не удалось загрузить расписание")

with tab2:
    st.subheader("🔍 Поиск свободных окон")
    if "schedule_df" in st.session_state:
        st.info("Данные загружены. Здесь будет поиск свободных окон.")
        min_duration = st.slider("Минимальная длительность окна (минут)", 60, 180, 90)
        if st.button("Найти свободные окна"):
            st.success("Найдено несколько свободных окон (пока заглушка)")
    else:
        st.warning("Сначала загрузите расписание на вкладке 'Обновление расписания'")

with tab3:
    st.subheader("📅 Планирование комиссий")
    st.info("Здесь будет удобная форма для подбора состава комиссии и свободного времени.")
    st.write("Пока доступно только после загрузки расписания.")

with tab4:
    st.subheader("📊 Статистика")
    if "schedule_df" in st.session_state:
        df = st.session_state.schedule_df
        st.metric("Всего занятий", len(df))
        st.dataframe(df.head(10))
    else:
        st.info("Загрузите расписание, чтобы увидеть статистику")

st.caption("Версия 0.2 • Парсер в разработке • Работает стабильно")
