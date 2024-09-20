import streamlit as st
import sqlitecloud
import pytz
from datetime import datetime
import pandas as pd


# Initialize session state variables for progress tracking
if 'daily_annotated' not in st.session_state:
    st.session_state.daily_annotated = 0
if 'total_annotated' not in st.session_state:
    st.session_state.total_annotated = 0

# Define target goals
# DAILY_TARGET = 125
# TOTAL_TARGET = 5000



# # Recalculate expected progress based on days passed and set targets
# expected_annotations = min(days_passed * DAILY_TARGET, TOTAL_TARGET)
# expected_annotations_yesterday = min((days_passed - 1) * DAILY_TARGET, TOTAL_TARGET)


# Initialize session state variables for history, current index, and flag
if 'history' not in st.session_state:
    st.session_state.history = []
if 'current_row_index' not in st.session_state:
    st.session_state.current_row_index = 0
if 'show_warning' not in st.session_state:
    st.session_state.show_warning = False

# Predefined list of valid annotator IDs
first = st.secrets["Annotatorid"]["first"]
second = st.secrets["Annotatorid"]["second"]
third = st.secrets["Annotatorid"]["third"]
forth = st.secrets["Annotatorid"]["forth"]
fifth = st.secrets["Annotatorid"]["fifth"]
valid_annotator_ids = [first, second, third, forth, fifth]

# Capture annotator ID at the start and store it in session state
if 'annotator_id' not in st.session_state:
    st.session_state.annotator_id = None

# Create a text input for the annotator ID
annotator_id_input = st.text_input("أدخل معرف المراجع (Annotator ID):")

# Update the session state once the annotator ID is entered
if annotator_id_input:
    st.session_state.annotator_id = annotator_id_input


# Set different DAILY_TARGET based on annotator_id
if st.session_state.annotator_id == first or st.session_state.annotator_id == second:
    DAILY_TARGET = 150  # Assign 100 for first and second annotators
    WORK_DAYS = 34 
    TOTAL_TARGET = DAILY_TARGET * WORK_DAYS
    start_date_str = "2024-09-20" 
elif st.session_state.annotator_id == third or st.session_state.annotator_id == forth or st.session_state.annotator_id == fifth:
    DAILY_TARGET = 5  # Assign 100 for first and second annotators
    WORK_DAYS = 34 
    TOTAL_TARGET = DAILY_TARGET * WORK_DAYS
    start_date_str = "2024-09-19" 
else:
    st.error("معرف المراجع غير صحيح. يرجى إدخال معرف صالح.")
    st.stop()  # Stop execution until a valid ID is provided

# Set the start date for the 30-day task
# start_date_str = "2024-09-15"  # Set your desired start date in 'YYYY-MM-DD' format
start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

# Get the current date in user's timezone
current_date = datetime.now(pytz.timezone('Asia/Riyadh')).date()

# Calculate how many days have passed since the start date
# days_passed = (current_date - start_date).days
days_passed = max(0, (current_date - start_date).days)


# Recalculate expected progress based on days passed and set targets
expected_annotations = min(days_passed * DAILY_TARGET, TOTAL_TARGET)
# expected_annotations_yesterday = min((days_passed - 1) * DAILY_TARGET, TOTAL_TARGET)
expected_annotations_yesterday = min(max(days_passed - 1, 0) * DAILY_TARGET, TOTAL_TARGET)


# # Check if the entered ID is valid
# if st.session_state.annotator_id not in valid_annotator_ids:
#     st.error("معرف المراجع غير صحيح. يرجى إدخال معرف صالح.")
#     st.stop()  # Stop execution until a valid ID is provided

# Initialize a list to store token mappings if not already done
if 'token_mappings' not in st.session_state:
    st.session_state.token_mappings = []

# Function to get the current time in the user's timezone
def get_local_time():
    user_timezone = pytz.timezone('Asia/Riyadh')
    local_time = datetime.now(user_timezone)
    return local_time.strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp


# Function to establish a fresh database connection
def get_db_connection():
    db_connect = st.secrets["dbcloud"]["db_connect"]
    db_name = st.secrets["dbcloud"]["db_name"]
    conn = sqlitecloud.connect(db_connect)
    conn.execute(f"USE DATABASE {db_name}")
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

# Function to fetch rows based on the processed state
def get_rows_by_processed(processed_status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM dialect_words WHERE processed = ?', (processed_status,))
    rows = c.fetchall()
    conn.close()  # Close the connection after fetching rows
    return rows

# Function to update the dialect_words table based on action
def update_dialect_words(id_ai, action):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE dialect_words SET processed = ? WHERE id_ai = ?', (action, id_ai))
    conn.commit()
    conn.close()  # Close the connection after updating

# Function to save the annotation with the annotator ID and localized datestamp
def save_annotation(id_ai, word, context):
    annotator_id = st.session_state.annotator_id  # Retrieve annotator ID from session state
    conn = get_db_connection()
    c = conn.cursor()

    # Get the current timestamp in the user's timezone
    local_timestamp = get_local_time()

    # Insert the annotation with the local timestamp
    c.execute('''
        INSERT INTO annotation_words_contexts (id_ai, word, context, annotator_id, datestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (id_ai, word, context, annotator_id, local_timestamp))

    conn.commit()
    conn.close()  # Close the connection after saving

    # Update progress
    st.session_state.daily_annotated += 1
    st.session_state.total_annotated += 1

# Function to tokenize text into words (simple whitespace tokenization)
def tokenize(text):
    return text.split()


def display_matching_contexts(selected_word):
    conn = get_db_connection()
    c = conn.cursor()

    # Query annotation_words_contexts table
    c.execute('''
        SELECT 'annotation_words_contexts' as source, context as text FROM annotation_words_contexts 
        WHERE context LIKE ? 
        AND instr(context, ?) > 0
    ''', (f'% {selected_word} %', selected_word))
    annotation_results = c.fetchall()

    # Query original_data table
    c.execute('''
        SELECT 'original_data' as source, source_text as text FROM original_data 
        WHERE source_text LIKE ? 
        AND instr(source_text, ?) > 0
    ''', (f'% {selected_word} %', selected_word))
    original_data_results = c.fetchall()

    conn.close()

    # Combine both result sets into one list
    all_results = annotation_results + original_data_results
    total_results = len(all_results)

    # Display the total number of results
    st.write(f"عدد الجمل المدخلة لهذه الكلمة = {total_results} وأدناه أمثلة عليها:")

    # If there are more than 10 results, only display the first 10
    if total_results > 10:
        all_results = all_results[:10]

    # Display the results
    if all_results:
        # st.write(f"عرض النتائج الأولى للكلمة المختارة '{selected_word}':")
        for result in all_results:
            source, text = result
            st.write(f"- {text}")



css = '''
<style>
    .element-container:has(>.stTextArea), .stTextArea {
        width: 100% !important;  /* Flexible width */
        max-width: 100%;  /* Ensure it doesn't exceed the container */
    }
    .stTextArea textarea {
        height: 60px;
        width: 100% !important;  /* Make text area responsive */
        max-width: 100%;  /* Ensure the textarea doesn't overflow */
    }
</style>
'''
def display_token_mapping(source_text, entity_id,saudi_dialect_word):
    # Tokenize the source text (tweet)
    source_tokens = tokenize(source_text)


    # Display the Saudi dialect word above the text area
    st.markdown(f'<p style="color:#F39C12; font-weight:bold; display:inline;">الكلمات السعودية المقترحة :</p> <span style="display:inline;">{saudi_dialect_word}</span>', unsafe_allow_html=True)
    st.markdown(" ")

    
    # Display the label for the source text (tweet) with custom color and reduce gap
    st.markdown(f'<p style="color:#F39C12; font-weight:bold; margin-bottom:0; padding-bottom:0;">الجملة المقترحة:</p>', unsafe_allow_html=True)
    edited_tweet = st.text_area("يرجى اختصار الجملة قدر المستطاع", value=source_text)

    # st.markdown("""
    # <p style='font-size:14px; color:gray;'>ملاحظة: إذا أردت اختيار كلمتين وليست كلمة واحدة فاضف علامة _ بين الكلمتين, على سبيل المثال: كيف_حالك</p>
    # """, unsafe_allow_html=True)

    st.markdown(f'<p style="color:#F39C12; font-weight:bold; margin-bottom:0; padding-bottom:0;">اختر كلمة من الجملة:</p>', unsafe_allow_html=True)

    # Dropdown to select a word from the (possibly edited) text
    selected_source_token = st.selectbox(" إذا أردت اختيار كلمتين وليست كلمة واحدة فاضف علامة _ بين الكلمتين في الجملة بالأعلى", tokenize(edited_tweet))

    # Query the database for this selected word as a whole word
    display_matching_contexts(selected_source_token)

    # Button to map the selected tokens (No changes to this part)
    if st.button("تعيين ارتباط"):
        # Append the mapping to the list of token mappings in session state
        st.session_state.token_mappings.append(f"{selected_source_token} -> {edited_tweet}")

    # Display the list of all token mappings
    if st.session_state.token_mappings:
        st.write("تم تعيين الارتباطات التالية:")
        for mapping in st.session_state.token_mappings:
            st.write(mapping)


# Function to handle processing a row and then move to the next one
def process_row_callback():
    # Check if token mappings exist
    if not st.session_state.token_mappings:
        st.session_state.show_warning = True  # Set a flag to show the warning
        return  # Do not proceed if no token mappings have been made
    else:
        st.session_state.show_warning = False  # Reset the warning flag if mappings exist

    # Get the current row to be processed
    row = rows[st.session_state.current_row_index]
    id_ai, tweet, saudi_dialect_word, processed = row

    # We only want to save the selected token (from the token mappings)
    # Assuming the token mappings are in the format "selected_token -> context"
    for token_mapping in st.session_state.token_mappings:
        selected_token, context = token_mapping.split(" -> ")

        # Save only the selected token and the corresponding context
        save_annotation(id_ai, selected_token, context)

    # Mark the row as processed
    update_dialect_words(id_ai, "yes")

    # Clear token mappings after processing
    st.session_state.token_mappings = []

    # Move to the next row after processing
    st.session_state.current_row_index = (st.session_state.current_row_index + 1) % len(rows)

# Function to handle rejecting a row
def reject_row_callback():
    row = rows[st.session_state.current_row_index]
    id_ai, tweet, saudi_dialect_word, processed = row
    
    # Mark the row as rejected
    update_dialect_words(id_ai, "reject")
    
    # Move to the next row after rejecting
    st.session_state.current_row_index = (st.session_state.current_row_index + 1) % len(rows)

# Function to fetch daily annotations for the specific annotator
def get_daily_annotations():
    today = datetime.now(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM annotation_words_contexts WHERE annotator_id = ? AND datestamp LIKE ?', 
              (st.session_state.annotator_id, f'{today}%'))
    count = c.fetchone()[0]
    conn.close()
    return count

# Function to fetch total annotations for the specific annotator
def get_total_annotations():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM annotation_words_contexts WHERE annotator_id = ?', 
              (st.session_state.annotator_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

# Fetch unprocessed rows (processed = "no") if not already fetched
if 'rows' not in st.session_state:
    st.session_state.rows = get_rows_by_processed("no")

rows = st.session_state.rows  # Use stored rows

# Check if we have any rows left to process
if rows and len(rows) > 0:
    # Ensure the current_row_index is within bounds
    if st.session_state.current_row_index >= len(rows):
        st.session_state.current_row_index = 0  # Reset index if it exceeds the number of rows

    # Handle row navigation
    row = rows[st.session_state.current_row_index]
    id_ai, tweet, saudi_dialect_word, processed = row

    # RTL Styling for Arabic and button enhancement
    st.markdown("""
        <style>
        .stApp {
            direction: RTL;
            text-align: right;
        }
        </style>
    """, unsafe_allow_html=True)

    # Update progress based on current annotations
    st.session_state.daily_annotated = get_daily_annotations()
    st.session_state.total_annotated = get_total_annotations()

    # Progress feedback
    st.write(f"تمت مراجعة {st.session_state.daily_annotated} من أصل {DAILY_TARGET} اليوم")
    daily_progress = min(st.session_state.daily_annotated / DAILY_TARGET, 1.0)  # Ensure progress does not exceed 100%
    st.progress(daily_progress)

    if days_passed == 0:
        st.markdown(f"""
            <p><strong>اليوم الأول للتقييم</strong>. لقد بدأت اليوم وقمت بإدخال <span style="color:#F39C12;">{st.session_state.total_annotated}</span> جمل.</p>
        """, unsafe_allow_html=True)
    elif st.session_state.total_annotated >= expected_annotations:
        st.markdown(f"""
            <p><strong>عمل مميز</strong>.. مرّت <span style="color:#F39C12;">{days_passed}</span> أيام وقمت بإدخال <span style="color:#F39C12;">{st.session_state.total_annotated}</span> جمل.. بزيادة <span style="color:#F39C12;">{st.session_state.total_annotated - expected_annotations}</span> عن العدد المطلوب.</p>
        """, unsafe_allow_html=True)
    elif st.session_state.total_annotated < expected_annotations:
        st.markdown(f"""
            <p><strong>تحتاج إلى زيادة المعدل اليومي لتغطي</strong> <span style="color:#F39C12;">{expected_annotations - st.session_state.total_annotated}</span> المتأخرة بالإضافة إلى مهمة اليوم.. مرّت <span style="color:#F39C12;">{days_passed}</span> أيام وقمت بإدخال <span style="color:#F39C12;">{st.session_state.total_annotated}</span> جمل.</p>
        """, unsafe_allow_html=True)

    # # Display feedback based on overall progress
    # if st.session_state.total_annotated >= expected_annotations_yesterday and st.session_state.total_annotated < expected_annotations:
    #     remaining_today = max(DAILY_TARGET - st.session_state.daily_annotated, 0)  # Ensure no negative values
    #     st.markdown(f"""
    #         <p><strong>أحسنت أنت تسير على الخطة</strong>.. مرّت <span style="color:#F39C12;">{days_passed}</span> أيام وقمت بادخال <span style="color:#F39C12;">{st.session_state.total_annotated}</span> جمل. استمر في ادخال <span style="color:#F39C12;">{remaining_today}</span> جملة لإكمال الهدف اليومي.</p>
    #     """, unsafe_allow_html=True)
    # elif st.session_state.total_annotated > expected_annotations:
    #     number_extra = st.session_state.total_annotated - expected_annotations
    #     st.markdown(f"""
    #         <p><strong>عمل مميز</strong>.. مرّت <span style="color:#F39C12;">{days_passed}</span> أيام وقمت بادخال <span style="color:#F39C12;">{st.session_state.total_annotated}</span> جمل.. بزيادة <span style="color:#F39C12;">{number_extra}</span> عن العدد المطلوب</p>
    #     """, unsafe_allow_html=True)
    # elif st.session_state.total_annotated < expected_annotations:
    #     number_behind = expected_annotations - st.session_state.total_annotated
    #     st.markdown(f"""
    #         <p><strong>تحتاج إلى زيادة المعدل اليومي لتغطي</strong> <span style="color:#F39C12;">{number_behind}</span> المتأخرة .. مرّت <span style="color:#F39C12;">{days_passed}</span> أيام وقمت بادخال <span style="color:#F39C12;">{st.session_state.total_annotated}</span> جمل</p>
    #     """, unsafe_allow_html=True)
    
    # Display token mapping interface
    display_token_mapping(tweet, id_ai, saudi_dialect_word)

    # Display warning if no token mappings have been made
    if st.session_state.show_warning:
        st.error("يرجى تعيين ارتباط الكلمة بالجملة قبل الانتقال إلى الصف التالي.")

    # Buttons for processing actions
    col1, col2 = st.columns([1, 1])

    with col1:
        st.button("التالي", on_click=process_row_callback)

    with col2:
        st.button("رفض", on_click=reject_row_callback)
else:
    st.write("لا توجد صفوف غير معالجة متاحة.")
