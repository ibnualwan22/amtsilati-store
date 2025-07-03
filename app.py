import sqlite3
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, send_from_directory
import os
import io
import requests
import functools
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

# --- Inisialisasi Aplikasi Flask ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'kunci-rahasia-yang-sangat-sulit-ditebak'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Konfigurasi RajaOngkir ---
# Ganti dengan API Key Anda yang benar dari RajaOngkir.com nanti
RAJAONGKIR_API_KEY = "GANTI_DENGAN_API_KEY_RAJAONGKIR_NANTI"
RAJAONGKIR_BASE_URL = "https://api.rajaongkir.com/starter"

# --- Custom Filter Rupiah ---
@app.template_filter('rupiah')
def format_rupiah(value):
    """Format angka menjadi string dengan pemisah ribuan (titik)."""
    if value is None: return ""
    return f"{int(value):,}".replace(",", ".")

# --- Fungsi Koneksi Database ---
def get_db_connection():
    conn = sqlite3.connect('instance/store.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Decorator untuk Mewajibkan Login ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# ================== STRUKTUR RUTE HALAMAN ==================

# --- Rute Halaman Publik ---
@app.route('/')
def home():
    # Alamat utama ('/') akan mengarahkan ke halaman toko.
    return redirect(url_for('shop_page'))

@app.route('/toko')
def shop_page():
    # Mengambil SEMUA kitab dari database, tidak hanya yang tersedia
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books ORDER BY name").fetchall()
    conn.close()
    # Kirim semua data kitab ke template
    return render_template('shop.html', books=books)

@app.route('/toko/kitab/<int:book_id>')
def book_detail(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    if book is None: return "Kitab tidak ditemukan.", 404
    return render_template('book_detail.html', book=book)

@app.route('/cek-ongkir')
def cek_ongkir_page():
    return render_template('cek_ongkir.html')


# --- Rute Halaman Admin ---
@app.route('/admin/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Username atau password salah!')
        else:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('admin_dashboard'))
            
    return render_template('login.html')

@app.route('/admin/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin.html')


# ================== SEMUA API (ENDPOINT DATA) ==================

# --- API UNTUK MANAJEMEN KITAB (Dilindungi) ---

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Menyediakan akses ke file yang diunggah."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/add-book', methods=['POST'])
@login_required
def add_book():
    # Mengambil data dari form, bukan JSON
    name = request.form['name']
    price = request.form['price']
    availability = request.form['availability']
    link_ig = request.form.get('link_ig')
    link_wa = request.form.get('link_wa')
    link_shopee = request.form.get('link_shopee')
    link_tiktok = request.form.get('link_tiktok')
    
    image_filename = None
    # Cek apakah ada file gambar yang diunggah
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename != '':
            # Amankan nama file dan simpan
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    try:
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO books (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok, image_filename)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok, image_filename)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Kitab baru berhasil ditambahkan!'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nama kitab sudah ada.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/all', methods=['GET'])
@login_required
def get_all_books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(row) for row in books])

@app.route('/api/books', methods=['GET'])
@login_required
def get_available_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE availability = 'Tersedia' ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(row) for row in books])

@app.route('/api/book/<int:book_id>', methods=['GET'])
@login_required
def get_book_details(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    if book is None:
        return jsonify({'error': 'Kitab tidak ditemukan'}), 404
    return jsonify(dict(book))

@app.route('/api/update-book', methods=['POST'])
@login_required
def update_book():
    # Mengambil semua data dari form
    book_id = request.form['id']
    name = request.form['name']
    price = request.form['price']
    availability = request.form['availability']
    link_ig = request.form.get('link_ig')
    link_wa = request.form.get('link_wa')
    link_shopee = request.form.get('link_shopee')
    link_tiktok = request.form.get('link_tiktok')

    # Gunakan nama yang konsisten dengan form di admin.html
    image_filename = request.form.get('existing_image_filename') 
    
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename != '':
            if image_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], image_filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
    
    try:
        conn = get_db_connection()
        conn.execute(
            """UPDATE books SET 
               name = ?, price = ?, availability = ?, link_ig = ?, link_wa = ?, 
               link_shopee = ?, link_tiktok = ?, image_filename = ?
               WHERE id = ?""",
            (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok, image_filename, book_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Data kitab berhasil diupdate!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    conn = get_db_connection()
    # Ambil nama file gambar sebelum dihapus dari database
    book = conn.execute('SELECT image_filename FROM books WHERE id = ?', (book_id,)).fetchone()
    
    try:
        # Hapus data dari database
        conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        
        # Jika ada file gambar terkait, hapus dari folder uploads
        if book and book['image_filename']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], book['image_filename'])
            if os.path.exists(image_path):
                os.remove(image_path)
                
        conn.close()
        return jsonify({'message': 'Kitab berhasil dihapus.'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


# --- API UNTUK PEMBELI & IMPORT (Dilindungi) ---
@app.route('/api/offline-buyers', methods=['GET'])
@login_required
def get_offline_buyers():
    conn = get_db_connection()
    buyers = conn.execute('SELECT * FROM offline_buyers ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(row) for row in buyers])

@app.route('/api/import-buyers', methods=['POST'])
@login_required
def import_buyers():
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        NAMA_KOLOM = 'Nama'
        ALAMAT_KOLOM = 'Alamat'
        ASRAMA_KOLOM = 'Asrama'
        df = pd.read_excel(filepath, dtype=str).fillna('')
        conn = get_db_connection()
        
        for index, row in df.iterrows():
            try:
                name = row[NAMA_KOLOM]
                address = row[ALAMAT_KOLOM]
                dormitory = row[ASRAMA_KOLOM]
                conn.execute('INSERT INTO offline_buyers (name, address, dormitory) VALUES (?, ?, ?)', (name, address, dormitory))
            except sqlite3.IntegrityError:
                conn.execute('UPDATE offline_buyers SET address = ?, dormitory = ? WHERE name = ?', (address, dormitory, name))
            except KeyError as e:
                return jsonify({'error': f"Kolom '{e.args[0]}' tidak ditemukan di file Excel."}), 400
        
        conn.commit()
        conn.close()
        os.remove(filepath)
        return jsonify({'message': 'Data pembeli berhasil diimpor/diupdate!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- API UNTUK REKAP PENJUALAN (Dilindungi) ---
@app.route('/api/add-offline-sale', methods=['POST'])
@login_required
def add_offline_sale():
    data = request.json
    try:
        conn = get_db_connection()
        book = conn.execute('SELECT price FROM books WHERE id = ?', (data['book_id'],)).fetchone()
        if not book: return jsonify({'error': 'Kitab tidak ditemukan'}), 404
        
        total_price = book['price'] * int(data['quantity'])
        
        conn.execute(
            'INSERT INTO offline_sales (buyer_id, book_id, quantity, total_price) VALUES (?, ?, ?, ?)',
            (data['buyer_id'], data['book_id'], data['quantity'], total_price)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Rekap offline berhasil ditambahkan!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-online-sale', methods=['POST'])
@login_required
def add_online_sale():
    data = request.json
    try:
        conn = get_db_connection()
        book = conn.execute('SELECT price FROM books WHERE id = ?', (data['book_id'],)).fetchone()
        if not book: return jsonify({'error': 'Kitab tidak ditemukan'}), 404
        
        quantity = int(data['quantity'])
        shipping_cost = 15000 # Contoh ongkir statis
        # Kalkulasi total harga baru: (harga kitab * jumlah) + ongkir
        total_price = (book['price'] * quantity) + shipping_cost

        conn.execute(
            # Tambahkan 'quantity' ke dalam statement INSERT
            'INSERT INTO online_sales (buyer_name, buyer_address, book_id, shipping_cost, total_price, transfer_date, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (data['buyer_name'], data['buyer_address'], data['book_id'], shipping_cost, total_price, data['transfer_date'], quantity)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Rekap online berhasil ditambahkan!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-offline-sales')
@login_required
def get_all_offline_sales():
    conn = get_db_connection()
    query = """
    SELECT os.id, ob.name as buyer_name, ob.address, ob.dormitory, b.name as book_name, 
           os.quantity, os.total_price, strftime('%d-%m-%Y %H:%M', os.sale_date) as sale_date_formatted
    FROM offline_sales os
    JOIN offline_buyers ob ON os.buyer_id = ob.id
    JOIN books b ON os.book_id = b.id
    ORDER BY os.id DESC
    """
    sales = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in sales])

@app.route('/api/recent-online-sales')
@login_required
def get_all_online_sales():
    conn = get_db_connection()
    query = """
    SELECT 
        os.id, os.buyer_name, os.buyer_address, b.name as book_name, os.shipping_cost, 
        os.total_price, os.quantity, -- Ambil data quantity
        strftime('%d-%m-%Y %H:%M', os.sale_date) as sale_date_formatted,
        strftime('%d-%m-%Y', os.transfer_date) as transfer_date_formatted
    FROM online_sales os
    JOIN books b ON os.book_id = b.id
    ORDER BY os.id DESC
    """
    sales = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in sales])

# --- API UNTUK EXPORT EXCEL (Dilindungi) ---
@app.route('/api/export-offline-sales')
@login_required
def export_offline():
    conn = get_db_connection()
    query = """
    SELECT strftime('%d-%m-%Y %H:%M', os.sale_date) as 'Tanggal Transaksi', ob.name as 'Nama Pembeli', 
           ob.address as 'Alamat', ob.dormitory as 'Asrama', b.name as 'Nama Kitab', os.quantity as 'Jumlah', 
           b.price as 'Harga Satuan', os.total_price as 'Total Harga'
    FROM offline_sales os
    JOIN offline_buyers ob ON os.buyer_id = ob.id
    JOIN books b ON os.book_id = b.id
    ORDER BY os.id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Rekap Offline')
    output.seek(0)
    return send_file(output, download_name='semua_rekap_offline.xlsx', as_attachment=True)

@app.route('/api/export-online-sales')
@login_required
def export_online():
    conn = get_db_connection()
    query = """
    SELECT 
        strftime('%d-%m-%Y %H:%M', os.sale_date) as 'Tanggal Transaksi', 
        strftime('%d-%m-%Y', os.transfer_date) as 'Tanggal Transfer',
        os.buyer_name as 'Nama Pembeli', os.buyer_address as 'Alamat Pengiriman', 
        b.name as 'Nama Kitab', os.quantity as 'Jumlah', -- Tambahkan kolom Jumlah
        b.price as 'Harga Kitab', os.shipping_cost as 'Ongkir', 
        os.total_price as 'Total Harga'
    FROM online_sales os
    JOIN books b ON os.book_id = b.id
    ORDER BY os.id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Rekap Online')
    output.seek(0)
    
    return send_file(output, download_name='semua_rekap_online.xlsx', as_attachment=True)

# --- API Publik untuk Ongkir ---
@app.route('/api/provinsi', methods=['GET'])
def get_provinsi():
    headers = {'key': RAJAONGKIR_API_KEY}
    try:
        response = requests.get(f"{RAJAONGKIR_BASE_URL}/province", headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(data['rajaongkir']['results'])
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Gagal menghubungi server RajaOngkir'}), 500
    except KeyError:
        return jsonify({'error': 'API Key RajaOngkir tidak valid'}), 401

@app.route('/api/kota/<prov_id>', methods=['GET'])
def get_kota(prov_id):
    headers = {'key': RAJAONGKIR_API_KEY}
    try:
        response = requests.get(f"{RAJAONGKIR_BASE_URL}/city?province={prov_id}", headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(data['rajaongkir']['results'])
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Gagal menghubungi server RajaOngkir'}), 500

@app.route('/api/cek-ongkir', methods=['POST'])
def post_cek_ongkir():
    data = request.json
    headers = {'key': RAJAONGKIR_API_KEY, 'content-type': "application/x-www-form-urlencoded"}
    payload = {
        'origin': '153', # ID Kabupaten Jepara
        'destination': data['destination_city_id'],
        'weight': data['weight'],
        'courier': 'jne'
    }
    try:
        response = requests.post(f"{RAJAONGKIR_BASE_URL}/cost", headers=headers, data=payload)
        response.raise_for_status()
        result = response.json()
        return jsonify(result['rajaongkir']['results'][0]['costs'])
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Gagal menghubungi server RajaOngkir'}), 500
    except (KeyError, IndexError):
        return jsonify({'error': 'Gagal memproses respons. Periksa kota tujuan.'}), 500

# --- BLOK UNTUK MENJALANKAN SERVER (HARUS SELALU DI PALING BAWAH) ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
