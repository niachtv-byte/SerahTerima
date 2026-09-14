import streamlit as st
import pandas as pd
import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Konfigurasi Halaman Web
st.set_page_config(
    page_title="Sistem Closing Kasir - RS Adhyaksa Jatim",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling UI
st.markdown("""
<style>
    .main-header { font-size: 24px; font-weight: bold; color: #1e4d2b; text-align: center; margin-bottom: 2px; }
    .sub-header { font-size: 15px; color: #444; text-align: center; margin-bottom: 20px; }
    .stButton>button { width: 100%; background-color: #1e4d2b; color: white; font-weight: bold; border-radius: 6px; }
    .stAlert { padding: 8px 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🏥 SISTEM INTEGRASI SERAH TERIMA CLOSING KASIR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Rumah Sakit Adhyaksa Jawa Timur</div>', unsafe_allow_html=True)

# Variables Default
penerimaan_tunai_simrs = 0.0
penerimaan_nontunai_simrs = 0.0
biaya_admin_simrs = 0.0

# 2. Sidebar Upload SIMRS
st.sidebar.header("📂 1. Upload Tarikan File SIMRS")
uploaded_file = st.sidebar.file_uploader("Unggah File Excel SIMRS (.xlsx)", type=["xlsx"])

df_raw = None
file_parsed = False

# Sidebar Form Tanggal & Shift
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filter Shift")
tgl_shift = st.sidebar.date_input("Tanggal Shift", value=datetime.date.today())
shift_opt = st.sidebar.selectbox("Shift Operasional", [
    "PAGI (07.00 - 14.00 WIB)",
    "SIANG (14.00 - 21.00 WIB)",
    "MALAM (21.00 - 07.00 WIB)"
])

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file)
        
        # Format pencarian kolom sensitif
        cols = {str(c).strip(): c for c in df_raw.columns}
        
        col_tgl = cols.get('Tanggal Transaksi') or cols.get('Tanggal')
        col_notx = cols.get('No. Transaksi') or cols.get('No Transaksi')
        col_jenis = cols.get('Jenis Pembayaran')
        col_total = cols.get('Total Transaksi')
        col_tipe_item = cols.get('Tipe Item')
        col_subtotal_item = cols.get('Subtotal Item')

        if col_tgl and col_notx and col_jenis and col_total:
            # Parse Tanggal
            df_raw['tgl_parsed'] = pd.to_datetime(df_raw[col_tgl], format='%d/%m/%Y', errors='coerce').dt.date
            
            # Filter sesuai tanggal shift yang dipilih
            df_filtered = df_raw[df_raw['tgl_parsed'] == tgl_shift]
            
            if not df_filtered.empty:
                # DEDUPLIKASI: Ambil 1 baris per No. Transaksi agar nominal tidak berlipat ganda
                df_tx_unique = df_filtered.groupby(col_notx).first().reset_index()
                
                # Pemisahan Tunai dan Non-Tunai
                is_cash = df_tx_unique[col_jenis].astype(str).str.upper().str.contains('CASH|TUNAI')
                
                penerimaan_tunai_simrs = float(df_tx_unique[is_cash][col_total].sum())
                penerimaan_nontunai_simrs = float(df_tx_unique[~is_cash][col_total].sum())
                
                # Biaya Admin EDC / QRIS dari detail item
                if col_tipe_item and col_subtotal_item:
                    admin_mask = (df_filtered[col_tipe_item] == 'Biaya Administrasi') & (~df_filtered[col_jenis].astype(str).str.upper().str.contains('CASH|TUNAI'))
                    biaya_admin_simrs = float(df_filtered[admin_mask][col_subtotal_item].sum())
                
                file_parsed = True
                st.sidebar.success(f"✅ Auto-Parse Berhasil!\nTerbaca {len(df_tx_unique)} Transaksi Unique")
            else:
                st.sidebar.warning(f"⚠️ Tidak ada transaksi pada tanggal {tgl_shift.strftime('%d/%m/%Y')}")
    except Exception as e:
        st.sidebar.error(f"❌ Gagal membaca file: {e}")
else:
    st.sidebar.info("📌 Silakan unggah file Excel SIMRS untuk mengisi nominal otomatis.")

# 3. Form Input Utama
with st.container():
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.subheader("📋 Data Petugas & Shift")
        petugas_lama = st.text_input("Petugas Shift Lama (Menyerahkan)", "CHORI CHOIRUNNISA'")
        petugas_baru = st.text_input("Petugas Shift Baru (Menerima)", "ABDUL JALIL SANTRI AJI")

    with col2:
        st.subheader("💰 Transaksi Tunai (Rp)")
        modal_awal = st.number_input("Saldo Awal Kas Shift (Modal Kembalian)", value=1141700.0, step=50000.0)
        penerimaan_tunai = st.number_input("Penerimaan Tunai Pelayanan", value=penerimaan_tunai_simrs, step=10000.0)
        piutang_tunai = st.number_input("Pelunasan Piutang Tunai", value=0.0, step=10000.0)
        deposit_tunai = st.number_input("Penerimaan Deposit Tunai", value=0.0, step=10000.0)
        refund_tunai = st.number_input("Dikurangi: Batal / Refund Tunai", value=0.0, step=10000.0)

    with col3:
        st.subheader("💳 Transaksi Non-Tunai (Rp)")
        penerimaan_nontunai = st.number_input("Penerimaan Non-Tunai Pelayanan", value=penerimaan_nontunai_simrs, step=50000.0)
        piutang_nontunai = st.number_input("Pelunasan Piutang Non-Tunai", value=0.0, step=10000.0)
        deposit_nontunai = st.number_input("Penerimaan Deposit Non-Tunai", value=0.0, step=10000.0)
        refund_nontunai = st.number_input("Dikurangi: Batal / Refund Non-Tunai", value=0.0, step=10000.0)
        total_biaya_admin = st.number_input("Total Biaya Admin EDC / QRIS (Rp)", value=biaya_admin_simrs, step=1000.0)

        # Hitung Netto Non-Tunai
        total_nontunai_bruto = penerimaan_nontunai + piutang_nontunai + deposit_nontunai - refund_nontunai
        total_nontunai_netto = total_nontunai_bruto - total_biaya_admin
        st.info(f"Netto Non-Tunai Masuk: **Rp {total_nontunai_netto:,.2f}**")

# 4. Rincian Fisik Uang Brankas (Cash Count)
st.markdown("---")
st.subheader("💵 Input Uang Fisik Kasir (Cash Count)")
st.caption("Masukkan lembar/keping uang yang ada di brankas saat closing.")

col_pec1, col_pec2, col_pec3, col_pec4 = st.columns(4)

with col_pec1:
    l100 = st.number_input("100.000 (Lembar)", min_value=0, value=8)
    l50 = st.number_input("50.000 (Lembar)", min_value=0, value=6)

with col_pec2:
    l20 = st.number_input("20.000 (Lembar)", min_value=0, value=2)
    l10 = st.number_input("10.000 (Lembar)", min_value=0, value=13)

with col_pec3:
    l5 = st.number_input("5.000 (Lembar)", min_value=0, value=16)
    l2 = st.number_input("2.000 (Lembar)", min_value=0, value=18)

with col_pec4:
    l1 = st.number_input("1.000 (Lembar/Keping)", min_value=0, value=1)
    logam = st.number_input("Total Uang Logam (Rp)", min_value=0.0, value=51700.0, step=100.0)

# Kertas Kalkulasi
total_tunai_netto = penerimaan_tunai + piutang_tunai + deposit_tunai - refund_tunai
total_kas_seharusnya = modal_awal + total_tunai_netto
total_uang_fisik = (l100 * 100000) + (l50 * 50000) + (l20 * 20000) + (l10 * 10000) + (l5 * 5000) + (l2 * 2000) + (l1 * 1000) + logam
selisih_kas = total_uang_fisik - total_kas_seharusnya
total_pendapatan_netto = total_tunai_netto + total_nontunai_netto

# 5. Rekapitulasi Ringkas
st.markdown("---")
st.subheader("📊 Rekonsiliasi Hasil Closing")
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric(label="Target Kas Fisik (Modal+Tunai)", value=f"Rp {total_kas_seharusnya:,.2f}")
with m2:
    st.metric(label="Uang Fisik Brankas", value=f"Rp {total_uang_fisik:,.2f}")
with m3:
    status_selisih = "PAS" if selisih_kas == 0 else ("LEBIH" if selisih_kas > 0 else "KURANG")
    st.metric(label=f"Selisih Kas ({status_selisih})", value=f"Rp {selisih_kas:,.2f}")
with m4:
    st.metric(label="Total Pendapatan Netto Shift", value=f"Rp {total_pendapatan_netto:,.2f}")

catatan_tambahan = st.text_area("Catatan Kasir Tambahan", "Uang fisik pas sesuai dengan rekapan.")

# 6. Generator PDF (Sesuai Form Resmi)
def create_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, alignment=1, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, alignment=1, spaceAfter=8)
    normal_bold = ParagraphStyle('NormalBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8)
    
    elements = []
    elements.append(Paragraph("RUMAH SAKIT ADHYAKSA JAWA TIMUR", title_style))
    elements.append(Paragraph("FORMULIR SERAH TERIMA CLOSING KASIR SHIFT", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e4d2b"), spaceAfter=8))
    
    # Metadata Header
    meta_data = [
        [Paragraph("<b>Tanggal Shift:</b>", normal_style), Paragraph(tgl_shift.strftime("%d/%m/%Y"), normal_style), Paragraph("<b>Petugas Menyerahkan:</b>", normal_style), Paragraph(petugas_lama, normal_style)],
        [Paragraph("<b>Shift Operasional:</b>", normal_style), Paragraph(shift_opt, normal_style), Paragraph("<b>Petugas Menerima:</b>", normal_style), Paragraph(petugas_baru, normal_style)]
    ]
    t_meta = Table(meta_data, colWidths=[90, 180, 110, 170])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F4F3")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 8))
    
    # Tabel Rekapitulasi Tunai & Non-Tunai
    elements.append(Paragraph("<b>1. REKAPITULASI PENERIMAAN KAS & NON-TUNAI</b>", normal_bold))
    rekap_data = [
        ["Uraian Transaksi", "Tunai (Rp)", "Non-Tunai (Rp)", "Biaya Admin (Rp)", "Netto (Rp)"],
        ["Saldo Awal Kas (Modal Kembalian)", f"{modal_awal:,.2f}", "-", "-", f"{modal_awal:,.2f}"],
        ["Penerimaan Pelayanan", f"{penerimaan_tunai:,.2f}", f"{penerimaan_nontunai:,.2f}", f"{total_biaya_admin:,.2f}", f"{(penerimaan_tunai + penerimaan_nontunai - total_biaya_admin):,.2f}"],
        ["Pelunasan Piutang", f"{piutang_tunai:,.2f}", f"{piutang_nontunai:,.2f}", "-", f"{(piutang_tunai + piutang_nontunai):,.2f}"],
        ["Penerimaan Deposit", f"{deposit_tunai:,.2f}", f"{deposit_nontunai:,.2f}", "-", f"{(deposit_tunai + deposit_nontunai):,.2f}"],
        ["Dikurangi: Batal / Refund", f"({refund_tunai:,.2f})", f"({refund_nontunai:,.2f})", "-", f"-({(refund_tunai + refund_nontunai):,.2f})"],
        ["TOTAL PENDAPATAN NETTO SHIFT", f"{total_tunai_netto:,.2f}", f"{total_nontunai_bruto:,.2f}", f"{total_biaya_admin:,.2f}", f"{total_pendapatan_netto:,.2f}"]
    ]
    t_rekap = Table(rekap_data, colWidths=[180, 95, 95, 90, 90])
    t_rekap.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e4d2b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E8F5E9")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_rekap)
    elements.append(Spacer(1, 8))
    
    # Tabel Rincian Cash Count
    elements.append(Paragraph("<b>2. RINCIAN PERHITUNGAN UANG FISIK (CASH COUNT)</b>", normal_bold))
    cash_data = [
        ["Pecahan", "Jumlah", "Total Nominal", "Pecahan", "Jumlah", "Total Nominal"],
        ["Rp 100.000", str(l100), f"Rp {l100*100000:,.2f}", "Rp 5.000", str(l5), f"Rp {l5*5000:,.2f}"],
        ["Rp 50.000", str(l50), f"Rp {l50*50000:,.2f}", "Rp 2.000", str(l2), f"Rp {l2*2000:,.2f}"],
        ["Rp 20.000", str(l20), f"Rp {l20*20000:,.2f}", "Rp 1.000", str(l1), f"Rp {l1*1000:,.2f}"],
        ["Rp 10.000", str(l10), f"Rp {l10*10000:,.2f}", "Uang Logam", "-", f"Rp {logam:,.2f}"],
        ["TOTAL UANG FISIK AKTUAL BRANKAS", "", "", "", "", f"Rp {total_uang_fisik:,.2f}"],
        ["KAS SEHARUSNYA (MODAL + TUNAI NETTO)", "", "", "", "", f"Rp {total_kas_seharusnya:,.2f}"],
        [f"SELISIH KAS ({status_selisih})", "", "", "", "", f"Rp {selisih_kas:,.2f}"]
    ]
    t_cash = Table(cash_data, colWidths=[90, 50, 135, 90, 50, 135])
    t_cash.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#444444")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (2,-1), 'RIGHT'),
        ('ALIGN', (4,0), (5,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('SPAN', (0,5), (4,5)),
        ('SPAN', (0,6), (4,6)),
        ('SPAN', (0,7), (4,7)),
        ('FONTNAME', (0,5), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor("#FFF3E0")),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_cash)
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph(f"<b>Catatan Tambahan:</b> {catatan_tambahan}", normal_style))
    elements.append(Spacer(1, 12))
    
    # Kolom Tanda Tangan
    sig_data = [
        ["Petugas Shift Lama (Menyerahkan)", "Petugas Shift Baru (Menerima)", "Mengetahui (Supervisor/Kasie)"],
        ["\n\n\n________________________", "\n\n\n________________________", "\n\n\n________________________"],
        [petugas_lama, petugas_baru, " ( .................................... ) "]
    ]
    t_sig = Table(sig_data, colWidths=[180, 180, 190])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    elements.append(t_sig)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

st.markdown("---")
st.subheader("🖨️ Cetak & Unduh Laporan PDF")
pdf_bytes = create_pdf()

st.download_button(
    label="📄 Unduh Form Closing Kasir (PDF)",
    data=pdf_bytes,
    file_name=f"Form_Serah_Terima_Kasir_{tgl_shift}.pdf",
    mime="application/pdf"
)
