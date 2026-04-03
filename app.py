import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

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
# SUPABASE INIT
# =========================
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"❌ Ошибка подключения к Supabase: {e}")
        return None


supabase = init_supabase()

if supabase:
    st.success("✅ Supabase подключен")
else:
    st.stop()

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("Настройки")

    if st.button("🔄 Обновить расписание", type="primary"):
        st.info("Парсер будет добавлен на следующем шаге")

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Обновление данных",
    "Поиск свободных окон",
    "Планирование комиссий",
    "Статистика",
    "Сохранённые"
])

# =========================
# TAB 1
# =========================
with tab1:
    st.subheader("Обновление расписания")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))

    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))

    if st.button("📥 Загрузить данные"):
        st.warning("Парсер ещё не подключён")

# =========================
# TEST QUERY
# =========================
with tab5:
    st.subheader("Проверка базы")

    try:
        response = supabase.table("schedules").select("*").limit(5).execute()
        data = response.data

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)
        else:
            st.info("Таблица пуста")
    except Exception as e:
        st.error(f"Ошибка запроса: {e}")



# =========================
# INSERT TEST DATA
# =========================
with tab1:
    st.subheader("Добавление тестовой записи")

    with st.form("add_schedule"):
        group_name = st.text_input("Группа", "3530902/20101")
        teacher = st.text_input("Преподаватель", "Иванов И.И.")
        subject = st.text_input("Предмет", "Математика")
        lesson_type = st.selectbox("Тип", ["Лекция", "Практика", "Лабораторная"])
        date = st.date_input("Дата")
        start_time = st.time_input("Начало")
        end_time = st.time_input("Конец")
        classroom = st.text_input("Аудитория", "101")

        submitted = st.form_submit_button("💾 Сохранить")

        if submitted:
            try:
                data = {
                    "group_name": group_name,
                    "teacher": teacher,
                    "subject": subject,
                    "lesson_type": lesson_type,
                    "date": str(date),
                    "start_time": str(start_time),
                    "end_time": str(end_time),
                    "classroom": classroom
                }

                supabase.table("schedules").insert(data).execute()

                st.success("✅ Запись добавлена")

            except Exception as e:
                st.error(f"Ошибка вставки: {e}")
