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

# ========================= ИНИЦИАЛИЗАЦИЯ SESSION STATE =========================
if 'schedule_data' not in st.session_state:
    st.session_state.schedule_data = {}  # Хранит {название: DataFrame}
if 'parsing_active' not in st.session_state:
    st.session_state.parsing_active = False
if 'parsing_stop' not in st.session_state:
    st.session_state.parsing_stop = False

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
        return "Не указано"
    
    link = place_element.find('a', class_='lesson__link')
    if not link:
        return "Не указано"
    
    place_text = link.get_text(strip=True)
    
    # Форматируем адрес
    place_text = re.sub(r'(\d)(ауд\.)', r'\1 \2', place_text)
    place_text = re.sub(r'(улица|ул\.)(\d)', r'\1 \2', place_text)
    place_text = re.sub(r'(\d)([а-яА-Я])', r'\1 \2', place_text)
    
    parts = [p.strip() for p in place_text.split(',') if p.strip()]
    unique_parts = []
    for part in parts:
        if part not in unique_parts:
            unique_parts.append(part)
    
    return ', '.join(unique_parts) if unique_parts else "Не указано"

# ========================= ПАРСЕР ГРУППЫ (ИСПРАВЛЕННЫЙ) =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        return

    group_id = GROUP_MAP[group_human]
    all_lessons = []
    current = start_date - timedelta(days=start_date.weekday())
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
        # Мгновенная проверка остановки
        if st.session_state.parsing_stop:
            st.warning("⛔ Парсинг остановлен пользователем")
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
                            # Берем последний span для названия предмета
                            if spans:
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

            # Обновляем прогресс
            progress = min(week_count / total_weeks, 1.0)
            
            # Возвращаем прогресс и текущий DataFrame
            if all_lessons:
                yield progress, pd.DataFrame(all_lessons)
            else:
                yield progress, pd.DataFrame()
            
            time.sleep(0.5)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {str(e)}")

        current += timedelta(weeks=1)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (ИСПРАВЛЕННЫЙ) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        return

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []
    current = start_date - timedelta(days=start_date.weekday())
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2
    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    while current <= end_date:
        # Мгновенная проверка остановки
        if st.session_state.parsing_stop:
            st.warning("⛔ Парсинг остановлен пользователем")
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
                            if spans:
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

                        place_elem = lesson.find('div', class_='lesson__places')
                        place = parse_place(place_elem)
                        
                        # Проверяем, что это наш преподаватель
                        teacher_element = lesson.find('div', class_='lesson__teachers')
                        is_our_teacher = False
                        if teacher_element:
                            teacher_links = teacher_element.find_all('a', href=lambda x: x and f'/teachers/{teacher_id}' in x)
                            if teacher_links:
                                is_our_teacher = True
                        
                        if is_our_teacher and subject:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Группы": ', '.join(groups),
                                "Преподаватель": teacher_name,
                                "Место": place,
                            })

            # Обновляем прогресс
            progress = min(week_count / total_weeks, 1.0)
            
            # Возвращаем прогресс и текущий DataFrame
            if all_lessons:
                yield progress, pd.DataFrame(all_lessons)
            else:
                yield progress, pd.DataFrame()
            
            time.sleep(0.5)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {str(e)}")

        current += timedelta(weeks=1)

# ========================= ФУНКЦИЯ ДЛЯ КАЛЕНДАРЯ =========================
def display_timeline_calendar(df, date):
    """Отображение расписания в виде временной шкалы"""
    if df.empty:
        st.info("Нет занятий на эту дату")
        return
    
    # Фильтруем по дате
    df_day = df[df['Дата'] == date].copy()
    if df_day.empty:
        st.info("Нет занятий на эту дату")
        return
    
    # Парсим время
    timeline_data = []
    for _, row in df_day.iterrows():
        time_parts = row['Время'].split('–')
        if len(time_parts) == 2:
            start = time_parts[0].strip()
            end = time_parts[1].strip()
            timeline_data.append({
                'start': start,
                'end': end,
                'subject': row['Дисциплина'],
                'type': row['Тип занятия'],
                'place': row.get('Место', ''),
                'teacher': row.get('Преподаватель', row.get('Группы', ''))
            })
    
    # Сортируем по времени начала
    timeline_data.sort(key=lambda x: x['start'])
    
    # Отображаем в виде таблицы
    for event in timeline_data:
        with st.container():
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"**{event['start']} - {event['end']}**")
            with col2:
                st.markdown(f"**{event['subject']}**")
                st.caption(f"📍 {event['place']} | 👨‍🏫 {event['teacher']} | 🏷️ {event['type']}")
            st.divider()

# ========================= ФУНКЦИЯ ПОИСКА СВОБОДНЫХ ОКОН =========================
def find_free_windows(selected_groups, selected_teachers, min_duration, start_date, end_date):
    """Поиск свободных окон между выбранными группами и преподавателями"""
    from collections import defaultdict
    
    all_busy_slots = []
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    total_items = len(selected_groups) + len(selected_teachers)
    if total_items == 0:
        return pd.DataFrame()
    
    current_item = 0
    
    # Парсинг групп
    for group in selected_groups:
        current_item += 1
        progress_text.text(f"Парсинг группы {group}... ({current_item}/{total_items})")
        progress_bar.progress(current_item / total_items)
        
        group_id = GROUP_MAP[group]
        current = start_date - timedelta(days=start_date.weekday())
        
        while current <= end_date:
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
                                if spans:
                                    subject = spans[-1].text.strip()
                            
                            time_str = lesson.find('span', class_='lesson__time')
                            time_str = time_str.text.strip() if time_str else ""
                            
                            if subject and time_str:
                                all_busy_slots.append({
                                    'date': date_text,
                                    'time': time_str,
                                    'subject': subject,
                                    'group': group
                                })
                time.sleep(0.3)
            except Exception as e:
                pass
            current += timedelta(weeks=1)
    
    # Парсинг преподавателей
    for teacher in selected_teachers:
        current_item += 1
        progress_text.text(f"Парсинг преподавателя {teacher}... ({current_item}/{total_items})")
        progress_bar.progress(current_item / total_items)
        
        teacher_id = TEACHER_MAP[teacher]
        current = start_date - timedelta(days=start_date.weekday())
        base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"
        
        while current <= end_date:
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
                                if spans:
                                    subject = spans[-1].text.strip()
                            
                            time_str = lesson.find('span', class_='lesson__time')
                            time_str = time_str.text.strip() if time_str else ""
                            
                            # Проверяем, что это наш преподаватель
                            teacher_element = lesson.find('div', class_='lesson__teachers')
                            is_our_teacher = False
                            if teacher_element:
                                teacher_links = teacher_element.find_all('a', href=lambda x: x and f'/teachers/{teacher_id}' in x)
                                if teacher_links:
                                    is_our_teacher = True
                            
                            if is_our_teacher and subject and time_str:
                                all_busy_slots.append({
                                    'date': date_text,
                                    'time': time_str,
                                    'subject': subject,
                                    'teacher': teacher
                                })
                time.sleep(0.3)
            except Exception as e:
                pass
            current += timedelta(weeks=1)
    
    progress_text.text("Анализ свободных окон...")
    
    # Группируем занятия по датам
    schedule_by_date = defaultdict(list)
    
    for slot in all_busy_slots:
        schedule_by_date[slot['date']].append(slot)
    
    # Ищем свободные окна
    free_windows = []
    
    for date, slots in schedule_by_date.items():
        # Сортируем по времени
        slots.sort(key=lambda x: x['time'])
        
        # Парсим время занятий
        busy_periods = []
        for slot in slots:
            time_parts = slot['time'].split('–')
            if len(time_parts) == 2:
                start = time_parts[0].strip()
                end = time_parts[1].strip()
                busy_periods.append((start, end, slot['subject']))
        
        # Ищем окна
        current_time = "09:00"
        for start, end, subject in busy_periods:
            # Вычисляем длительность окна в минутах
            try:
                current_h, current_m = map(int, current_time.split(':'))
                start_h, start_m = map(int, start.split(':'))
                
                current_min = current_h * 60 + current_m
                start_min = start_h * 60 + start_m
                
                duration = start_min - current_min
                if duration >= min_duration:
                    free_windows.append({
                        'Дата': date,
                        'Начало': current_time,
                        'Конец': start,
                        'Длительность (мин)': duration,
                        'После занятия': subject if busy_periods else 'Начало дня'
                    })
                
                current_time = end
            except:
                pass
        
        # Окно после последнего занятия
        try:
            end_h, end_m = map(int, current_time.split(':'))
            end_min = end_h * 60 + end_m
            day_end_min = 18 * 60  # 18:00
            duration = day_end_min - end_min
            if duration >= min_duration:
                free_windows.append({
                    'Дата': date,
                    'Начало': current_time,
                    'Конец': "18:00",
                    'Длительность (мин)': duration,
                    'После занятия': 'Конец дня'
                })
        except:
            pass
    
    progress_bar.empty()
    progress_text.empty()
    
    return pd.DataFrame(free_windows)

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2, tab3 = st.tabs(["📥 Обновление расписания", "🔍 Поиск свободных окон", "📊 Статистика"])

# ==================== ВКЛАДКА 1: ОБНОВЛЕНИЕ РАСПИСАНИЯ ====================
with tab1:
    st.subheader("Загрузка расписания")
    
    # Показываем сохраненные результаты
    if st.session_state.schedule_data:
        st.info(f"📌 Загружено расписаний: {len(st.session_state.schedule_data)}")
        for name, df in st.session_state.schedule_data.items():
            with st.expander(f"📋 {name} ({len(df)} занятий)"):
                st.dataframe(df, use_container_width=True)
    
    mode = st.radio("Что парсим?", ["Группу", "Преподавателя"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))
    
    # Кнопки управления
    col_buttons = st.columns(2)
    
    with col_buttons[0]:
        if mode == "Группу":
            group_human = st.selectbox("Выберите группу", list(GROUP_MAP.keys()))
            if st.button("🚀 Запустить парсинг группы", type="primary", disabled=st.session_state.parsing_active):
                st.session_state.parsing_active = True
                st.session_state.parsing_stop = False
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                final_df = pd.DataFrame()
                
                for progress, partial_df in parse_group_schedule(group_human, start_date, end_date):
                    if st.session_state.parsing_stop:
                        break
                    progress_bar.progress(progress)
                    status_text.text(f"Прогресс: {int(progress * 100)}%")
                    if not partial_df.empty:
                        final_df = partial_df
                
                if not final_df.empty and not st.session_state.parsing_stop:
                    st.session_state.schedule_data[f"Группа {group_human}"] = final_df
                    st.success(f"✅ Загружено {len(final_df)} занятий")
                    st.dataframe(final_df, use_container_width=True)
                elif st.session_state.parsing_stop:
                    st.warning("Парсинг остановлен")
                else:
                    st.error("Не удалось загрузить расписание")
                
                st.session_state.parsing_active = False
                st.rerun()
        
        else:
            teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
            if st.button("🚀 Запустить парсинг преподавателя", type="primary", disabled=st.session_state.parsing_active):
                st.session_state.parsing_active = True
                st.session_state.parsing_stop = False
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                final_df = pd.DataFrame()
                
                for progress, partial_df in parse_teacher_schedule(teacher_name, start_date, end_date):
                    if st.session_state.parsing_stop:
                        break
                    progress_bar.progress(progress)
                    status_text.text(f"Прогресс: {int(progress * 100)}%")
                    if not partial_df.empty:
                        final_df = partial_df
                
                if not final_df.empty and not st.session_state.parsing_stop:
                    st.session_state.schedule_data[f"Преподаватель {teacher_name}"] = final_df
                    st.success(f"✅ Загружено {len(final_df)} занятий")
                    st.dataframe(final_df, use_container_width=True)
                elif st.session_state.parsing_stop:
                    st.warning("Парсинг остановлен")
                else:
                    st.error("Не удалось загрузить расписание")
                
                st.session_state.parsing_active = False
                st.rerun()
    
    with col_buttons[1]:
        if st.button("⛔ Остановить парсинг", disabled=not st.session_state.parsing_active):
            st.session_state.parsing_stop = True
            st.warning("Остановка парсинга...")

# ==================== ВКЛАДКА 2: ПОИСК СВОБОДНЫХ ОКОН ====================
with tab2:
    st.subheader("🔍 Поиск свободных окон")
    
    st.write("**Выберите группы и преподавателей для поиска:**")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    with col2:
        selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))
    
    # Выбор длительности окна
    duration_options = {
        "30 минут": 30,
        "1 час": 60,
        "1.5 часа": 90,
        "2 часа": 120
    }
    selected_duration = st.selectbox("Мин. длительность окна", list(duration_options.keys()))
    min_duration = duration_options[selected_duration]
    
    # Выбор периода
    col3, col4 = st.columns(2)
    with col3:
        search_start = st.date_input("Начало поиска", datetime(2026, 2, 1), key="search_start")
    with col4:
        search_end = st.date_input("Конец поиска", datetime(2026, 2, 28), key="search_end")
    
    if st.button("🔎 Найти свободные окна", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя")
        else:
            with st.spinner("Поиск свободных окон..."):
                free_windows_df = find_free_windows(selected_groups, selected_teachers, min_duration, search_start, search_end)
                
                if not free_windows_df.empty:
                    st.success(f"✅ Найдено {len(free_windows_df)} свободных окон")
                    st.dataframe(free_windows_df, use_container_width=True)
                    
                    # Детальный вывод
                    st.subheader("📋 Список свободных окон:")
                    for _, window in free_windows_df.iterrows():
                        st.write(f"📅 **{window['Дата']}**: {window['Начало']} – {window['Конец']} (⏱ {window['Длительность (мин)']} мин)")
                else:
                    st.warning("Свободные окна не найдены")
    
    # Календарь с расписанием (если есть загруженные данные)
    if st.session_state.schedule_data:
        st.subheader("📅 Календарь расписания")
        
        # Собираем все расписания в один DataFrame
        all_dfs = []
        for name, df in st.session_state.schedule_data.items():
            all_dfs.append(df)
        
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            unique_dates = sorted(combined_df['Дата'].unique())
            
            if unique_dates:
                selected_date = st.selectbox("Выберите дату для просмотра", unique_dates, key="calendar_date")
                display_timeline_calendar(combined_df, selected_date)

# ==================== ВКЛАДКА 3: СТАТИСТИКА ====================
with tab3:
    st.subheader("📊 Статистика")
    
    if st.session_state.schedule_data:
        # Объединяем все расписания
        all_dfs = []
        for name, df in st.session_state.schedule_data.items():
            all_dfs.append(df)
        
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            
            st.metric("Всего занятий", len(combined_df))
            st.metric("Период", f"{combined_df['Дата'].min()} — {combined_df['Дата'].max()}")
            st.metric("Загружено расписаний", len(st.session_state.schedule_data))
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**По типам занятий:**")
                st.dataframe(combined_df['Тип занятия'].value_counts(), use_container_width=True)
            
            with col2:
                if 'Преподаватель' in combined_df.columns:
                    st.write("**По преподавателям:**")
                    st.dataframe(combined_df['Преподаватель'].value_counts().head(10), use_container_width=True)
                elif 'Группы' in combined_df.columns:
                    st.write("**По группам:**")
                    st.dataframe(combined_df['Группы'].value_counts().head(10), use_container_width=True)
            
            st.write("**По местам проведения (топ 10):**")
            if 'Место' in combined_df.columns:
                st.dataframe(combined_df['Место'].value_counts().head(10), use_container_width=True)
    else:
        st.info("Загрузите расписание на вкладке 'Обновление расписания'")

st.caption("Версия 3.1 • Исправлен парсинг • Работают и группы, и преподаватели")
