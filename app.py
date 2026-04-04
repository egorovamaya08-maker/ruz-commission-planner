import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")
st.markdown("**Планирование**")

# ========================= СЛОВАРИ ДЛЯ ПРЕОБРАЗОВАНИЯ =========================
# Добавляй сюда новые группы в формате: "человеческий_номер": "внутренний_id"
GROUP_MAP = {
    "3733801/50001": "41846",
    "3733801/50002": "41847",
    "3733801/50003": "41848",
    "3733801/50004": "41849",
    # ← Добавляй новые группы сюда ниже
    # "3733801/XXXXX": "XXXXX",
}

# Словарь преподавателей (имя → id). Будет полезен позже для поиска свободных окон у преподавателей
TEACHER_MAP = {
    "Зайцев Андрей Александрович": "19997",
    "Благова Ирина Юрьевна": "23640",
    # ← Добавляй новых преподавателей сюда
}

# ========================= ПАРСЕР =========================
def parse_schedule(group_human: str, start_date: datetime, end_date: datetime):
    """Основной парсер с использованием твоего GROUP_MAP"""
    
    if group_human not in GROUP_MAP:
        st.error(f"❌ Группа {group_human} не найдена в словаре. Добавьте её в GROUP_MAP.")
        return pd.DataFrame()
    
    group_id = GROUP_MAP[group_human]
    lessons = []
    
    st.info(f"Парсим группу **{group_human}** (внутренний ID: {group_id})")
    
    current = start_date - timedelta(days=start_date.weekday())
    total_weeks = ((end_date - start_date).days // 7) + 2
    week_count = 0
    
    progress_bar = st.progress(0)
    
    while current <= end_date:
        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Здесь будет полноценный парсинг твоего оригинального кода
                # Пока используем заглушку для тестирования интерфейса
                lessons.append({
                    "date": current.strftime("%Y-%m-%d"),
                    "group_human": group_human,
                    "group_id": group_id,
                    "discipline": "Дисциплина (парсер в разработке)",
                    "lesson_type": "Лекция",
                    "teachers": "Преподаватель",
                    "time_start": "10:00",
                    "time_end": "11:30"
                })
                
            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(10)   # Важная пауза для сайта ruz
            
        except Exception as e:
            st.warning(f"Ошибка на неделе {current.strftime('%Y-%m-%d')}: {e}")
        
        current += timedelta(weeks=1)
    
    df = pd.DataFrame(lessons)
    return df

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Обновление расписания", 
    "🔍 Поиск свободных окон", 
    "📅 Планирование комиссий", 
    "📊 Статистика"
])

with tab1:
    st.subheader("Загрузка расписания")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))
    
    # Выбор группы из списка + возможность ввести новую
    group_options = list(GROUP_MAP.keys())
    group_human = st.selectbox("Выберите группу", group_options, index=0)
    
    # Возможность добавить новую группу вручную
    if st.checkbox("Добавить новую группу (не из списка)"):
        group_human = st.text_input("Введите номер группы", "3733801/50005")
    
    if st.button("🚀 Запустить парсинг расписания", type="primary"):
        with st.spinner("Парсинг расписания..."):
            df = parse_schedule(group_human, start_date, end_date)
            
            if not df.empty:
                st.session_state.schedule_df = df
                st.success(f"✅ Загружено {len(df)} записей для группы {group_human}")
                st.dataframe(df)
            else:
                st.error("Не удалось загрузить расписание")

with tab2:
    st.subheader("🔍 Поиск свободных окон")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        st.success("Данные загружены!")
        min_duration = st.slider("Минимальная длительность окна (мин)", 60, 240, 90)
        if st.button("Найти свободные окна"):
            st.info("Поиск свободных окон будет добавлен на следующем шаге")
    else:
        st.warning("Сначала загрузите расписание")

with tab3:
    st.subheader("📅 Планирование комиссий")
    st.info("Эта вкладка будет работать после улучшения парсера и добавления данных.")

with tab4:
    st.subheader("📊 Статистика")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        st.metric("Всего занятий", len(df))
        st.dataframe(df)
    else:
        st.info("Загрузите расписание для просмотра статистики")

st.caption("Версия 0.4 • Словарь групп подключён • Парсер в разработке")
