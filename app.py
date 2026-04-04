import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re
from collections import defaultdict

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")
st.markdown("**Поиск свободных окон и планирование • СПбГТУ**")

# Инициализация session state для сохранения данных
if 'schedule_df' not in st.session_state:
    st.session_state.schedule_df = None
if 'parsing_stop' not in st.session_state:
    st.session_state.parsing_stop = False
if 'last_parse_info' not in st.session_state:
    st.session_state.last_parse_info = None

# ========================= СЛОВАРИ =========================
GROUP_MAP = {
    "3733801/50001": "41846",
    "3733801/50002": "41847",
    "3733801/50003": "41848",
    "3733801/50004": "41849",
    "3743809/40101": "42004",
}

TEACHER_MAP = {
    "Зайцев Андрей Александрович": "19997",
    "Благова Ирина Юрьевна": "23640",
    "Степанова Ксения Сергеевна": "20342",
}

# ========================= ФУНКЦИИ ПАРСИНГА МЕСТА =========================
def parse_place(place_element):
    """Парсинг места проведения из элемента lesson__places"""
    if not place_element:
        return ""
    
    # Ищем ссылку с классом lesson__link
    link = place_element.find('a', class_='lesson__link')
    if not link:
        return ""
    
    # Получаем текст
    place_text = link.get_text(strip=True)
    
    # Добавляем пробел перед "ауд." если его нет
    place_text = re.sub(r'(\d)(ауд\.)', r'\1 \2', place_text)
    place_text = re.sub(r'(улица|ул\.)(\d)', r'\1 \2', place_text)
    place_text = re.sub(r'(\d)([а-яА-Я])', r'\1 \2', place_text)
    
    # Форматируем: убираем дублирование
    parts = [p.strip() for p in place_text.split(',') if p.strip()]
    
    # Убираем дубликаты
    unique_parts = []
    for part in parts:
        if part not in unique_parts:
            unique_parts.append(part)
    
    # Собираем обратно
    result = ', '.join(unique_parts)
    
    return result if result else "СДО"

# ========================= ПАРСЕР ГРУППЫ =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime, progress_callback=None, stop_check=None):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
        # Проверка на остановку
        if stop_check and stop_check():
            st.warning("Парсинг остановлен пользователем.")
            break

        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        lesson_type = lesson.find('div', class_='lesson__type')
                        lesson_type = lesson_type.text.strip() if lesson_type else ""

                        teachers = []
                        teachers_elem = lesson.find('div', class_='lesson__teachers')
                        if teachers_elem:
                            for a in teachers_elem.find_all('a'):
                                name = a.text.strip()
                                if name and len(name) > 3:
                                    teachers.append(name)

                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""

                        # Используем новую функцию парсинга места
                        place_elem = lesson.find('div', class_='lesson__places')
                        place = parse_place(place_elem)

                        if subject and teachers:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Преподаватель": ", ".join(teachers),
                                "Место": place,
                                "Группа": group_human,
                            })

            if progress_callback:
                progress_callback(min(week_count / total_weeks, 1.0))
            time.sleep(12)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (обновленный с местом) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime, progress_callback=None, stop_check=None):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    while current <= end_date:
        # Проверка на остановку
        if stop_check and stop_check():
            st.warning("Парсинг остановлен пользователем.")
            break

        week_count += 1
        url = f"{base_url}?date={current.strftime('%Y-%m-%d')}"

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        lesson_type = lesson.find('div', class_='lesson__type')
                        lesson_type = lesson_type.text.strip() if lesson_type else ""

                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""

                        groups = []
                        groups_elem = lesson.find('div', class_='lesson-groups__list')
                        if groups_elem:
                            for link in groups_elem.find_all('a', class_='lesson__link'):
                                groups.append(link.text.strip())

                        # Используем новую функцию парсинга места
                        place_elem = lesson.find('div', class_='lesson__places')
                        place = parse_place(place_elem)

                        if subject:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Группы": ', '.join(groups),
                                "Преподаватель": teacher_name,
                                "Место": place,
                            })

            if progress_callback:
                progress_callback(min(week_count / total_weeks, 1.0))
            time.sleep(12)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ФУНКЦИЯ ПОИСКА СВОБОДНЫХ ОКОН =========================
def find_free_windows(df, selected_groups, selected_teachers, min_duration, break_min, start_time, end_time, days_of_week):
    """Поиск свободных окон между занятиями"""
    if df.empty:
        return []
    
    # Фильтруем по выбранным группам и преподавателям
    mask_groups = df['Группа'].isin(selected_groups) if 'Группа' in df.columns else pd.Series([False] * len(df))
    mask_teachers = df['Преподаватель'].isin(selected_teachers) if 'Преподаватель' in df.columns else pd.Series([False] * len(df))
    
    # Если выбраны и группы, и преподаватели
    if selected_groups and selected_teachers:
        df_filtered = df[mask_groups | mask_teachers]
    elif selected_groups:
        df_filtered = df[mask_groups]
    elif selected_teachers:
        df_filtered = df[mask_teachers]
    else:
        df_filtered = df
    
    if df_filtered.empty:
        return []
    
    # Преобразуем даты
    df_filtered['Дата_объект'] = pd.to_datetime(df_filtered['Дата'], format='%d.%m.%Y', errors='coerce')
    
    # Словарь для хранения занятий по дням
    schedule_by_day = defaultdict(list)
    
    for _, row in df_filtered.iterrows():
        if pd.isna(row['Дата_объект']):
            continue
            
        # Парсим время
        time_parts = row['Время'].split('–')
        if len(time_parts) != 2:
            continue
            
        start_time_str = time_parts[0].strip()
        end_time_str = time_parts[1].strip()
        
        try:
            start_dt = datetime.strptime(start_time_str, '%H:%M')
            end_dt = datetime.strptime(end_time_str, '%H:%M')
            
            schedule_by_day[row['Дата_объект'].date()].append({
                'start': start_dt.time(),
                'end': end_dt.time(),
                'subject': row['Дисциплина'],
                'type': row['Тип занятия'],
                'place': row.get('Место', ''),
                'teacher': row.get('Преподаватель', row.get('Группы', ''))
            })
        except:
            continue
    
    # Поиск свободных окон
    free_windows = []
    day_names_ru = {
        'Monday': 'Пн', 'Tuesday': 'Вт', 'Wednesday': 'Ср',
        'Thursday': 'Чт', 'Friday': 'Пт', 'Saturday': 'Сб', 'Sunday': 'Вс'
    }
    
    for date, lessons in schedule_by_day.items():
        day_name_ru = day_names_ru[date.strftime('%A')]
        if day_name_ru not in days_of_week:
            continue
        
        # Сортируем занятия по времени начала
        lessons.sort(key=lambda x: x['start'])
        
        # Начало рабочего дня
        current_time = start_time
        
        # Проверяем окно до первого занятия
        if lessons:
            first_start = lessons[0]['start']
            delta = (datetime.combine(date, first_start) - datetime.combine(date, current_time)).seconds / 60
            if delta >= min_duration:
                free_windows.append({
                    'Дата': date.strftime('%d.%m.%Y'),
                    'День недели': day_name_ru,
                    'Начало': current_time.strftime('%H:%M'),
                    'Конец': first_start.strftime('%H:%M'),
                    'Длительность (мин)': int(delta)
                })
        
        # Проверяем окна между занятиями
        for i in range(len(lessons) - 1):
            current_end = lessons[i]['end']
            next_start = lessons[i + 1]['start']
            
            # Добавляем перерыв после занятия
            current_end = (datetime.combine(date, current_end) + timedelta(minutes=break_min)).time()
            
            delta = (datetime.combine(date, next_start) - datetime.combine(date, current_end)).seconds / 60
            if delta >= min_duration:
                free_windows.append({
                    'Дата': date.strftime('%d.%m.%Y'),
                    'День недели': day_name_ru,
                    'Начало': current_end.strftime('%H:%M'),
                    'Конец': next_start.strftime('%H:%M'),
                    'Длительность (мин)': int(delta)
                })
        
        # Проверяем окно после последнего занятия
        if lessons:
            last_end = lessons[-1]['end']
            # Добавляем перерыв после последнего занятия
            last_end = (datetime.combine(date, last_end) + timedelta(minutes=break_min)).time()
            
            if last_end < end_time:
                delta = (datetime.combine(date, end_time) - datetime.combine(date, last_end)).seconds / 60
                if delta >= min_duration:
                    free_windows.append({
                        'Дата': date.strftime('%d.%m.%Y'),
                        'День недели': day_name_ru,
                        'Начало': last_end.strftime('%H:%M'),
                        'Конец': end_time.strftime('%H:%M'),
                        'Длительность (мин)': int(delta)
                    })
    
    return sorted(free_windows, key=lambda x: (x['Дата'], x['Начало']))

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2, tab3 = st.tabs(["📥 Обновление расписания", "🔍 Поиск свободных окон", "📊 Статистика"])

with tab1:
    st.subheader("Загрузка расписания")
    
    # Показываем информацию о последнем парсинге
    if st.session_state.last_parse_info:
        st.info(f"📌 Последний парсинг: {st.session_state.last_parse_info}")
    
    mode = st.radio("Что парсим?", ["Группу", "Преподавателя"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))
    
    # Кнопка остановки парсинга
    if 'parsing_active' not in st.session_state:
        st.session_state.parsing_active = False
    
    col_button1, col_button2 = st.columns(2)
    
    with col_button1:
        if mode == "Группу":
            group_human = st.selectbox("Выберите группу", list(GROUP_MAP.keys()))
            if st.button("🚀 Запустить парсинг группы", type="primary") and not st.session_state.parsing_active:
                st.session_state.parsing_active = True
                st.session_state.parsing_stop = False
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(progress):
                    progress_bar.progress(progress)
                    status_text.text(f"Прогресс: {int(progress * 100)}%")
                
                def check_stop():
                    return st.session_state.parsing_stop
                
                df = parse_group_schedule(group_human, start_date, end_date, update_progress, check_stop)
                
                if not df.empty:
                    st.session_state.schedule_df = df
                    st.session_state.last_parse_info = f"Группа {group_human}, {len(df)} занятий, {start_date} - {end_date}"
                    st.success(f"✅ Загружено {len(df)} занятий для группы {group_human}")
                    
                    # Показываем результат
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])
                elif not st.session_state.parsing_stop:
                    st.error("Не удалось загрузить расписание")
                
                st.session_state.parsing_active = False
        
        else:
            teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
            if st.button("🚀 Запустить парсинг преподавателя", type="primary") and not st.session_state.parsing_active:
                st.session_state.parsing_active = True
                st.session_state.parsing_stop = False
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(progress):
                    progress_bar.progress(progress)
                    status_text.text(f"Прогресс: {int(progress * 100)}%")
                
                def check_stop():
                    return st.session_state.parsing_stop
                
                df = parse_teacher_schedule(teacher_name, start_date, end_date, update_progress, check_stop)
                
                if not df.empty:
                    st.session_state.schedule_df = df
                    st.session_state.last_parse_info = f"Преподаватель {teacher_name}, {len(df)} занятий, {start_date} - {end_date}"
                    st.success(f"✅ Загружено {len(df)} занятий для преподавателя {teacher_name}")
                    
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])
                elif not st.session_state.parsing_stop:
                    st.error("Не удалось загрузить расписание")
                
                st.session_state.parsing_active = False
    
    with col_button2:
        if st.session_state.parsing_active:
            if st.button("⛔ Остановить парсинг", key="stop_parsing"):
                st.session_state.parsing_stop = True
                st.warning("Остановка парсинга...")

with tab2:
    st.subheader("🔍 Поиск свободных окон")
    
    if st.session_state.schedule_df is not None and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        
        st.write("**Выберите группы и преподавателей для поиска общего свободного времени:**")
        
        # Получаем уникальные значения из DataFrame
        available_groups = sorted(df['Группа'].unique()) if 'Группа' in df.columns else []
        available_teachers = sorted(df['Преподаватель'].unique()) if 'Преподаватель' in df.columns else []
        
        col1, col2 = st.columns(2)
        with col1:
            selected_groups = st.multiselect("Группы", options=available_groups, default=available_groups[:1] if available_groups else [])
        with col2:
            selected_teachers = st.multiselect("Преподаватели", options=available_teachers, default=available_teachers[:1] if available_teachers else [])
        
        col3, col4, col5 = st.columns(3)
        with col3:
            min_duration = st.slider("Мин. длительность окна (мин)", 30, 180, 80, key="min_duration")
            break_min = st.slider("Мин. перерыв после занятия (мин)", 0, 60, 20, key="break_min")
        with col4:
            start_time = st.time_input("Начало интервала", datetime.strptime("09:00", "%H:%M").time(), key="start_time")
            end_time = st.time_input("Конец интервала", datetime.strptime("18:00", "%H:%M").time(), key="end_time")
        with col5:
            days_of_week = st.multiselect("Дни недели", ["Пн", "Вт", "Ср", "Чт", "Пт"], default=["Пн", "Вт", "Ср", "Чт", "Пт"], key="days_of_week")
        
        if st.button("🔎 Найти свободные окна", type="primary"):
            with st.spinner("Поиск свободных окон..."):
                free_windows = find_free_windows(df, selected_groups, selected_teachers, min_duration, break_min, start_time, end_time, days_of_week)
                
                if free_windows:
                    st.success(f"✅ Найдено {len(free_windows)} свободных окон")
                    windows_df = pd.DataFrame(free_windows)
                    st.dataframe(windows_df, use_container_width=True)
                    
                    # Детальный вывод
                    st.subheader("📋 Детальный список окон:")
                    for window in free_windows:
                        st.write(f"📅 **{window['Дата']} ({window['День недели']})**: {window['Начало']} – {window['Конец']} (⏱ {window['Длительность (мин)']} мин)")
                else:
                    st.warning("Свободные окна не найдены")
        
        # Показываем расписание в виде календаря
        st.subheader("📅 Текущее расписание")
        
        # Выбираем даты для отображения
        unique_dates = sorted(df['Дата'].unique())
        if unique_dates:
            selected_date = st.selectbox("Выберите дату для просмотра расписания", unique_dates)
            df_day = df[df['Дата'] == selected_date]
            
            if not df_day.empty:
                # Сортируем по времени
                df_day_sorted = df_day.sort_values('Время')
                st.dataframe(df_day_sorted[['Время', 'Дисциплина', 'Тип занятия', 'Преподаватель', 'Место', 'Группа']], 
                           use_container_width=True)
    else:
        st.warning("Сначала загрузите расписание на вкладке 'Обновление расписания'")

with tab3:
    st.subheader("📊 Статистика")
    if st.session_state.schedule_df is not None and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        st.metric("Всего занятий", len(df))
        st.metric("Период", f"{df['Дата'].min()} — {df['Дата'].max()}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**По типам занятий:**")
            st.dataframe(df['Тип занятия'].value_counts())
        
        with col2:
            if 'Преподаватель' in df.columns:
                st.write("**По преподавателям:**")
                st.dataframe(df['Преподаватель'].value_counts())
            elif 'Группы' in df.columns:
                st.write("**По группам:**")
                st.dataframe(df['Группы'].value_counts())
        
        # Статистика по местам проведения
        st.write("**По местам проведения:**")
        if 'Место' in df.columns:
            place_stats = df['Место'].value_counts().head(10)
            st.dataframe(place_stats)
    else:
        st.info("Загрузите расписание для просмотра статистики")

st.caption("Версия 2.0 • Парсинг с реальными адресами • Сохранение результатов • Поиск свободных окон")
