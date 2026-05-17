import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import os

# إعدادات صفحة الويب لتناسب شاشات التابلت بمرونة باللمس
st.set_page_config(page_title="برنامج طباعة الملصقات الذكي", layout="wide")

# محاولة تحميل الخط العربي المرفوع للمشروع لضمان عمله على سيرفر لينكس (Streamlit Cloud)
@st.cache_resource
def load_pdf_font():
    font_path = "Amiri-Bold.ttf"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('ArabicAmiriBold', font_path))
            return 'ArabicAmiriBold'
        except:
            return 'Helvetica-Bold'
    return 'Helvetica-Bold'

font_name = load_pdf_font()

def find_column(columns, possibilities):
    for col in columns:
        if str(col).strip().lower() in possibilities:
            return col
    return None

st.title("🏷️ برنامج طباعة الملصقات الذكي")
st.write("ارفع ملف الإكسيل، اختر الأسماء، وحمّل ملف الـ PDF جاهزاً للطباعة فوراً.")

# 1. زر رفع ملف الإكسيل
uploaded_file = st.file_uploader("1. اختر ملف الإكسيل من جهازك", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        columns = df.columns
        
        first_col = find_column(columns, ['الاسم الأول', 'الاسم الاول', 'الاسم', 'اسم'])
        father_col = find_column(columns, ['اسم الأب', 'اسم الاب', 'الأب', 'الاب', 'اسم الأب الثاني', 'اسم الجد'])
        last_col = find_column(columns, ['اسم العائلة', 'العائلة', 'عائلة', 'الكنية', 'اللقب'])
        
        if not last_col:
            st.error("❌ لم يتم العثور على عمود اسم العائلة في الملف!")
        else:
            # ترتيب البيانات أبجدياً حسب العائلة
            df = df.sort_values(by=last_col)
            
            st.success(f"📦 تم تحميل {len(df)} اسم بنجاح مفرزة عائلياً.")
            st.write("### 👈 اختر الأسماء التي تريد طباعتها:")
            
            # تجهيز قائمة الأسماء
            names_list = []
            for index, row in df.iterrows():
                first_name = str(row[first_col]).strip() if first_col else ''
                father_name = str(row[father_col]).strip() if father_col else ''
                last_name = str(row[last_col]).strip()
                
                if first_name == 'nan': first_name = ''
                if father_name == 'nan': father_name = ''
                if last_name == 'nan': last_name = ''
                
                display_name = f"{last_name} {first_name} {father_name}".strip()
                display_name = " ".join(display_name.split())
                
                names_list.append({
                    "display": display_name,
                    "first": first_name,
                    "father": father_name,
                    "last": last_name
                })
            
            # عرض الأسماء في شبكة أفقية متجاوبة تناسب اللمس (6 أعمدة)
            selected_indices = []
            cols = st.columns(6)
            
            for idx, person in enumerate(names_list):
                with cols[idx % 6]:
                    if st.checkbox(person["display"], key=f"user_{idx}"):
                        selected_indices.append(idx)
            
            st.markdown("---")
            
            # 2. زر توليد وتنزيل الـ PDF
            if len(selected_indices) > 0:
                st.write(f"🟢 عدد الأسماء المختارة حالياً: **{len(selected_indices)}**")
                
                # إنشاء ملف الـ PDF في الذاكرة لتنزيله مباشرة
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                elements = []
                
                selected_names_processed = []
                for idx in selected_indices:
                    p = names_list[idx]
                    print_name = f"{p['first']} {p['father']} {p['last']}".strip()
                    print_name = " ".join(print_name.split())
                    
                    reshaped_text = arabic_reshaper.reshape(print_name)
                    bidi_text = get_display(reshaped_text)
                    selected_names_processed.append(bidi_text)
                
                grid_data = []
                row = []
                for name in selected_names_processed:
                    row.append(name)
                    if len(row) == 3:
                        grid_data.append(row)
                        row = []
                if row:
                    while len(row) < 3:
                        row.append("")
                    grid_data.append(row)
                
                if grid_data:
                    # بناء الجدول وتطبيق خط Amiri العربي المرفوع وتكبير الحجم
                    t = Table(grid_data, colWidths=[180, 180, 180], rowHeights=[90]*len(grid_data))
                    t.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                        ('FONTNAME', (0,0), (-1,-1), font_name),  # ربط الخط المحدث هنا
                        ('FONTSIZE', (0,0), (-1,-1), 20),         # حجم خط كبير وواضح للملصقات
                        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                        ('BOX', (0,0), (-1,-1), 1, colors.grey),
                    ]))
                    elements.append(t)
                    doc.build(elements)
                    
                    # زر التنزيل المخصص للويب والتابلت
                    st.download_button(
                        label="🔥 2. اضغط هنا لتحميل ملف PDF وجاهز للطباعة",
                        data=pdf_buffer.getvalue(),
                        file_name="labels_print.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.info("💡 الرجاء تحديد اسم واحد على الأثل من الشبكة أعلاه لتفعيل زر الطباعة.")
                
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
