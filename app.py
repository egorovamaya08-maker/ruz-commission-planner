import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
from bs4 import BeautifulSoup
import json
import time

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="RUZ Commission Planner",
    page_icon="📅",
    layout="wide"
)

st.title("📅 RUZ Commission Planner")
st.markdown("**Планирование комиссий и поиск свободных окон • СПбПУ**")

# =========================
# SUPABASE INIT WITH ERROR HANDLING
# =========================
@st.cache_resource
def init_supabase() -> Client:
    """Инициализация подключения к Supabase"""
    try:
        # Проверяем наличие секретов
        if "SUPABASE_URL" not in st.secrets:
            st.error("❌ SUPABASE_URL не найден в secrets.toml")
            return None
        if "SUPABASE_KEY" not in st.secrets:
            st.error("❌ SUPABASE_KEY не найден в secrets.toml")
            return None
            
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        # Валидация URL
        if not url.startswith("https://"):
            st.error("❌ Неверный формат SUPABASE_URL")
            return None
            
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"❌ Ошибка подключения к Supabase: {str(e)}")
        return None

# =========================
# PARSER FUNCTIONS
# =========================
@st.cache_data(ttl=3600)  # Кэшируем на 1 час
def parse_schedule_ruz(group_id, start_date, end_date):
    """
    Парсер расписания с ruz.spbstu.ru
    Адаптировано из Colab скриптов
    """
    try:
        # Базовый URL для API RUZ
        base_url = "https://ruz.spbstu.ru/api/v1/ruz"
        
        # Получаем расписание для группы
        # Формат дат: YYYY-MM-DD
        url = f"{base_url}/scheduler/{group_id}"
        
        params = {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            lessons = []
            
            for item in data:
                # Парсим каждое занятие
                lesson = {
                    "group_name": item.get("group", {}).get("name", ""),
                    "teacher": item.get("lecturer", ""),
                    "subject": item.get("discipline", ""),
                    "lesson_type": item.get("kind", ""),
                    "date": item.get("date", ""),
                    "start_time": item.get("begin", ""),
                    "end_time": item.get("end", ""),
                    "classroom": item.get("auditorium", ""),
                    "building": item.get("building", ""),
                    "week": item.get("week", 0)
                }
                lessons.append(lesson)
            
            return lessons
        else:
            st.error(f"Ошибка API: {response.status_code}")
            return []
            
    except requests.Timeout:
        st.error("Таймаут при запросе к RUZ")
        return []
    except Exception as e:
        st.error(f"Ошибка парсинга: {str(e)}")
        return []

@st.cache_data(ttl=86400)  # Кэшируем на день
def get_groups_list():
    """Получение списка групп с RUZ"""
    try:
        url = "https://ruz.spbstu.ru/api/v1/ruz/groups"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            groups = response.json()
            # Создаем словарь {название: id}
            groups_dict = {g["name"]: g["id"] for g in groups}
            return groups_dict
        else:
            return {}
    except Exception as e:
        st.error(f"Ошибка получения списка групп: {str(e)}")
        return {}

# =========================
# SUPABASE OPERATIONS
# =========================
def save_schedule_to_db(supabase_client, lessons):
    """Сохранение расписания в базу данных"""
    if not supabase_client or not lessons:
        return 0
    
    saved_count = 0
    for lesson in lessons:
        try:
            # Проверяем, существует ли уже такая запись
            existing = supabase_client.table("schedules")\
                .select("*")\
                .eq("date", lesson["date"])\
                .eq("group_name", lesson["group_name"])\
                .eq("start_time", lesson["start_time"])\
                .execute()
            
            if not existing.data:
                supabase_client.table("schedules").insert(lesson).execute()
                saved_count += 1
        except Exception as e:
            st.warning(f"Не удалось сохранить запись: {str(e)}")
            continue
    
    return saved_count

# =========================
# UI COMPONENTS
# =========================
def find_free_windows(supabase_client, start_date, end_date, duration_minutes=90):
    """Поиск свободных окон для комиссий"""
    try:
        # Получаем все занятия за период
        response = supabase_client.table("schedules")\
            .select("*")\
            .gte("date", start_date.strftime("%Y-%m-%d"))\
            .lte("date", end_date.strftime("%Y-%m-%d"))\
            .execute()
        
        if not response.data:
            return []
        
        df = pd.DataFrame(response.data)
        df['start_datetime'] = pd.to_datetime(df['date'] + ' ' + df['start_time'])
        df['end_datetime'] = pd.to_datetime(df['date'] + ' ' + df['end_time'])
        
        # Группируем по датам и ищем окна
        free_windows = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Только будни
                day_lessons = df[df['date'] == current_date.strftime("%Y-%m-%d")]
                
                # Рабочие часы: 9:00 - 18:00
                work_start = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=9)
                work_end = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=18)
                
                if len(day_lessons) == 0:
                    # Свободный день целиком
                    free_windows.append({
                        "date": current_date,
                        "start_time": "09:00",
                        "end_time": "18:00",
                        "duration_minutes": 540
                    })
                else:
                    # Ищем окна между занятиями
                    sorted_lessons = day_lessons.sort_values('start_datetime')
                    prev_end = work_start
                    
                    for _, lesson in sorted_lessons.iterrows():
                        if lesson['start_datetime'] > prev_end:
                            gap = (lesson['start_datetime'] - prev_end).seconds / 60
                            if gap >= duration_minutes:
                                free_windows.append({
                                    "date": current_date,
                                    "start_time": prev_end.strftime("%H:%M"),
                                    "end_time": lesson['start_datetime'].strftime("%H:%M"),
                                    "duration_minutes": gap
                                })
                        prev_end = max(prev_end, lesson['end_datetime'])
                    
                    # Окно после последнего занятия
                    if work_end > prev_end:
                        gap = (work_end - prev_end).seconds / 60
                        if gap >= duration_minutes:
                            free_windows.append({
                                "date": current_date,
                                "start_time": prev_end.strftime("%H:%M"),
                                "end_time": work_end.strftime("%H:%M"),
                                "duration_minutes": gap
                            })
            
            current_date += timedelta(days=1)
        
        return free_windows
    except Exception as e:
        st.error(f"Ошибка поиска окон: {str(e)}")
        return []

# =========================
# MAIN APP
# =========================
def main():
    # Инициализация Supabase
    supabase = init_supabase()
    
    if not supabase:
        st.error("❌ Не удалось подключиться к Supabase. Проверьте настройки.")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Управление")
        
        # Статус подключения
        st.success("✅ Supabase подключен")
        
        # Кнопка обновления расписания
        if st.button("🔄 Обновить расписание", type="primary"):
            st.session_state.show_parser = True
        
        st.divider()
        
        # Информация о группах
        if st.button("📚 Загрузить список групп"):
            with st.spinner("Загрузка списка групп..."):
                groups = get_groups_list()
                if groups:
                    st.session_state.groups = groups
                    st.success(f"Загружено {len(groups)} групп")
                else:
                    st.error("Не удалось загрузить группы")
    
    # Основные вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 Обновление данных",
        "🔍 Поиск окон",
        "📅 Планирование комиссий",
        "📊 Статистика"
    ])
    
    # TAB 1: Обновление данных
    with tab1:
        st.subheader("Загрузка расписания из RUZ")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
        with col2:
            end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))
        
        # Выбор группы
        group_name = st.text_input("Номер группы", "3530902/20101")
        
        if st.button("📥 Парсить и сохранить", type="primary"):
            if not group_name:
                st.warning("Введите номер группы")
            else:
                with st.spinner("Парсинг расписания..."):
                    lessons = parse_schedule_ruz(group_name, start_date, end_date)
                    
                    if lessons:
                        st.success(f"Получено {len(lessons)} занятий")
                        
                        # Сохраняем в БД
                        saved = save_schedule_to_db(supabase, lessons)
                        st.success(f"Сохранено {saved} новых записей")
                        
                        # Показываем пример
                        st.dataframe(pd.DataFrame(lessons[:10]))
                    else:
                        st.error("Не удалось загрузить расписание")
        
        st.divider()
        
        # Ручное добавление
        with st.expander("➕ Ручное добавление занятия"):
            with st.form("manual_add"):
                col1, col2 = st.columns(2)
                with col1:
                    group = st.text_input("Группа")
                    teacher = st.text_input("Преподаватель")
                    subject = st.text_input("Предмет")
                with col2:
                    lesson_type = st.selectbox("Тип", ["Лекция", "Практика", "Лабораторная", "Консультация", "Экзамен"])
                    date = st.date_input("Дата")
                    classroom = st.text_input("Аудитория")
                
                col3, col4 = st.columns(2)
                with col3:
                    start_time = st.time_input("Начало", datetime.strptime("10:00", "%H:%M").time())
                with col4:
                    end_time = st.time_input("Конец", datetime.strptime("11:30", "%H:%M").time())
                
                submitted = st.form_submit_button("💾 Сохранить")
                
                if submitted and group:
                    try:
                        data = {
                            "group_name": group,
                            "teacher": teacher,
                            "subject": subject,
                            "lesson_type": lesson_type,
                            "date": str(date),
                            "start_time": str(start_time),
                            "end_time": str(end_time),
                            "classroom": classroom
                        }
                        supabase.table("schedules").insert(data).execute()
                        st.success("✅ Занятие добавлено")
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)}")
    
    # TAB 2: Поиск свободных окон
    with tab2:
        st.subheader("Поиск свободных окон для комиссий")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_start = st.date_input("Начало периода", datetime.now())
        with col2:
            search_end = st.date_input("Конец периода", datetime.now() + timedelta(days=30))
        with col3:
            min_duration = st.number_input("Мин. длительность (мин)", value=90, step=30)
        
        if st.button("🔍 Найти свободные окна"):
            with st.spinner("Поиск..."):
                windows = find_free_windows(supabase, search_start, search_end, min_duration)
                
                if windows:
                    st.success(f"Найдено {len(windows)} свободных окон")
                    
                    # Группируем по датам
                    df_windows = pd.DataFrame(windows)
                    df_windows['date'] = pd.to_datetime(df_windows['date']).dt.date
                    
                    for date in df_windows['date'].unique():
                        with st.expander(f"📅 {date}"):
                            day_windows = df_windows[df_windows['date'] == date]
                            for _, window in day_windows.iterrows():
                                st.info(f"🕐 {window['start_time']} - {window['end_time']} (Длительность: {int(window['duration_minutes'])} мин)")
                else:
                    st.warning("Свободных окон не найдено")
    
    # TAB 3: Планирование комиссий
    with tab3:
        st.subheader("Планирование комиссий")
        st.info("ℹ️ Выберите свободное окно и запланируйте комиссию")
        
        # Здесь можно добавить форму для создания комиссий
        
    # TAB 4: Статистика
    with tab4:
        st.subheader("Статистика загруженных данных")
        
        try:
            # Общая статистика
            total = supabase.table("schedules").select("*", count="exact").execute()
            st.metric("Всего занятий в БД", total.count)
            
            # Группировка по типам занятий
            if total.count > 0:
                all_data = supabase.table("schedules").select("*").execute()
                df_stats = pd.DataFrame(all_data.data)
                
                if not df_stats.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("По типам занятий")
                        type_stats = df_stats['lesson_type'].value_counts()
                        st.dataframe(type_stats)
                    
                    with col2:
                        st.subheader("По группам")
                        group_stats = df_stats['group_name'].value_counts().head(10)
                        st.dataframe(group_stats)
        except Exception as e:
            st.error(f"Ошибка загрузки статистики: {str(e)}")

if __name__ == "__main__":
    main()
