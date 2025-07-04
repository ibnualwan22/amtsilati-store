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

# Konfigurasi folder upload dengan path absolut
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB file size
app.config['SECRET_KEY'] = 'kunci-rahasia-yang-sangat-sulit-ditebak'

# Buat folder uploads jika belum ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"Created upload folder at: {UPLOAD_FOLDER}")

# Ekstensi file yang diperbolehkan
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Konfigurasi RajaOngkir ---
BITESHIP_API_KEY = "biteship_live.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiYW10c2lsYXRpIHN0b3JlIiwidXNlcklkIjoiNjg2NWNhNGI4MzA3ZjgwMDEzNzY5NWQ5IiwiaWF0IjoxNzUxNjEwMzQ1fQ.hJAwHsYKTUWmhB6UvOeoLHGFIq0OA7y3yEAW4U5pwBA"
BITESHIP_BASE_URL = "https://api.biteship.com"

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

# --- Rute untuk melayani file upload ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Menyediakan akses ke file yang diunggah."""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        # Jika file tidak ditemukan, kembalikan placeholder
        return redirect('https://placehold.co/400x600/e2e8f0/4a5568?text=Gambar+Tidak+Ditemukan'), 404

# --- Rute Halaman Publik ---
@app.route('/')
def home():
    return redirect(url_for('shop_page'))

@app.route('/toko')
def shop_page():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books ORDER BY name").fetchall()
    conn.close()
    return render_template('shop.html', books=books)

@app.route('/toko/kitab/<int:book_id>')
def book_detail(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    books = conn.execute("SELECT * FROM books ORDER BY name").fetchall()
    conn.close()
    if book is None: 
        return "Kitab tidak ditemukan.", 404
    return render_template('book_detail.html', book=book, books=books)

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
@app.route('/api/add-book', methods=['POST'])
@login_required
def add_book():
    try:
        # Mengambil data dari form
        name = request.form['name']
        price = request.form['price']
        availability = request.form['availability']
        link_ig = request.form.get('link_ig', '')
        link_wa = request.form.get('link_wa', '')
        link_shopee = request.form.get('link_shopee', '')
        link_tiktok = request.form.get('link_tiktok', '')
        
        image_filename = None
        
        # Cek apakah ada file gambar yang diunggah
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                # Generate nama file yang aman dan unik
                original_filename = secure_filename(image_file.filename)
                # Tambahkan timestamp untuk menghindari duplikasi
                import time
                timestamp = str(int(time.time()))
                image_filename = f"{timestamp}_{original_filename}"
                
                # Simpan file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                image_file.save(filepath)
                print(f"Image saved to: {filepath}")

        # Simpan ke database
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
        print(f"Error adding book: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-book', methods=['POST'])
@login_required
def update_book():
    try:
        book_id = request.form['id']
        name = request.form['name']
        price = request.form['price']
        availability = request.form['availability']
        link_ig = request.form.get('link_ig', '')
        link_wa = request.form.get('link_wa', '')
        link_shopee = request.form.get('link_shopee', '')
        link_tiktok = request.form.get('link_tiktok', '')

        # Gunakan nama file yang ada
        image_filename = request.form.get('existing_image_filename', '')
        
        # Cek apakah ada file baru yang diupload
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                # Hapus file lama jika ada
                if image_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], image_filename)):
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    except:
                        pass
                
                # Generate nama file baru
                original_filename = secure_filename(image_file.filename)
                import time
                timestamp = str(int(time.time()))
                image_filename = f"{timestamp}_{original_filename}"
                
                # Simpan file baru
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                image_file.save(filepath)
                print(f"New image saved to: {filepath}")
        
        # Update database
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
        print(f"Error updating book: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT image_filename FROM books WHERE id = ?', (book_id,)).fetchone()
    
    try:
        conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        
        # Hapus file gambar jika ada
        if book and book['image_filename']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], book['image_filename'])
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    print(f"Deleted image: {image_path}")
                except:
                    pass
                
        conn.close()
        return jsonify({'message': 'Kitab berhasil dihapus.'})
    except Exception as e:
        conn.close()
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

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
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
    buyer_id = data.get('buyer_id')
    items = data.get('items', [])

    if not buyer_id or not items:
        return jsonify({'error': 'Data tidak lengkap'}), 400

    conn = get_db_connection()
    try:
        for item in items:
            book = conn.execute('SELECT price FROM books WHERE id = ?', (item['book_id'],)).fetchone()
            if not book:
                raise ValueError(f"Kitab dengan ID {item['book_id']} tidak ditemukan")
            
            total_price = book['price'] * int(item['quantity'])
            conn.execute(
                'INSERT INTO offline_sales (buyer_id, book_id, quantity, total_price) VALUES (?, ?, ?, ?)',
                (buyer_id, item['book_id'], item['quantity'], total_price)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
    
    return jsonify({'message': 'Transaksi offline berhasil disimpan!'})

# === API BARU: Penjualan Online Multi-Item ===
@app.route('/api/add-online-sale', methods=['POST'])
@login_required
def add_online_sale():
    data = request.json
    buyer_name = data.get('buyer_name')
    buyer_address = data.get('buyer_address')
    transfer_date = data.get('transfer_date')
    shipping_cost = data.get('shipping_cost', 0)
    items = data.get('items', [])

    if not all([buyer_name, buyer_address, transfer_date, items]):
        return jsonify({'error': 'Data tidak lengkap'}), 400

    conn = get_db_connection()
    try:
        # Bagi ongkir ke setiap item (atau bisa juga ditambahkan di akhir)
        # Di sini, kita asumsikan ongkir adalah biaya tetap untuk seluruh transaksi
        total_items_price = 0
        for item in items:
            book = conn.execute('SELECT price FROM books WHERE id = ?', (item['book_id'],)).fetchone()
            if not book:
                raise ValueError(f"Kitab dengan ID {item['book_id']} tidak ditemukan")
            total_items_price += book['price'] * int(item['quantity'])

        # Simpan setiap item sebagai entri terpisah tapi dengan referensi yang sama (jika diperlukan)
        # Untuk kesederhanaan, kita bisa simpan satu entri dengan total, atau per item.
        # Di sini kita tetap simpan per item agar konsisten.
        for item in items:
            book = conn.execute('SELECT price FROM books WHERE id = ?', (item['book_id'],)).fetchone()
            # Kalkulasi total per item (harga kitab * jumlah) + (ongkir / jumlah item)
            item_total_price = (book['price'] * int(item['quantity'])) + (shipping_cost / len(items))
            
            conn.execute(
                'INSERT INTO online_sales (buyer_name, buyer_address, book_id, shipping_cost, total_price, transfer_date, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (buyer_name, buyer_address, item['book_id'], (shipping_cost / len(items)), item_total_price, transfer_date, item['quantity'])
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
        
    return jsonify({'message': 'Transaksi online berhasil disimpan!'})


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
        os.total_price, os.quantity,
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
        b.name as 'Nama Kitab', os.quantity as 'Jumlah',
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


@app.route('/api/dashboard-stats')
@login_required
def get_dashboard_stats():
    conn = get_db_connection()
    
    # Total Kitab
    total_books = conn.execute('SELECT COUNT(id) FROM books').fetchone()[0]
    
    # Total Pembeli
    total_buyers = conn.execute('SELECT COUNT(id) FROM offline_buyers').fetchone()[0]
    
    # Penjualan bulan ini
    current_month = datetime.now().strftime('%Y-%m')
    
    total_offline_sales = conn.execute(
        "SELECT SUM(total_price) FROM offline_sales WHERE strftime('%Y-%m', sale_date) = ?", 
        (current_month,)
    ).fetchone()[0] or 0

    total_online_sales = conn.execute(
        "SELECT SUM(total_price) FROM online_sales WHERE strftime('%Y-%m', sale_date) = ?", 
        (current_month,)
    ).fetchone()[0] or 0

    conn.close()
    
    return jsonify({
        'total_books': total_books,
        'total_buyers': total_buyers,
        'total_offline_sales': total_offline_sales,
        'total_online_sales': total_online_sales
    })

# --- API Publik untuk Ongkir ---
@app.route('/api/cari-area', methods=['GET'])
def search_areas():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    headers = {'Authorization': f'Bearer {BITESHIP_API_KEY}'}
    url = f"{BITESHIP_BASE_URL}/v1/maps/areas?countries=ID&input={query}&type=single"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data['success'] and data['areas']:
            return jsonify(data['areas'])
        return jsonify([])
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cek-ongkir', methods=['POST'])
def post_cek_ongkir_biteship():
    data = request.json
    headers = {
        'Authorization': f'Bearer {BITESHIP_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        "origin_area_id": "IDNP6IDNC10", 
        "destination_area_id": data['destination_area_id'],
        "couriers": "jnt,jne,sicepat",
        "items": [{
            "name": "Paket Kitab",
            "description": "Pembelian dari Amtsilati Store",
            "value": 50000,
            "weight": int(data['weight']),
            "height": 5,
            "width": 15,
            "length": 20
        }]
    }
    
    try:
        response = requests.post(f"{BITESHIP_BASE_URL}/v1/rates/couriers", headers=headers, json=payload)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            return jsonify(result.get('pricing', []))
        else:
            error_message = result.get('error', 'Gagal mengambil data ongkir. Periksa kembali input Anda.')
            return jsonify({'error': error_message}), 400
            
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

# --- Debug route untuk cek upload folder ---
@app.route('/debug/check-uploads')
@login_required
def check_uploads():
    """Route untuk debugging - cek isi folder uploads"""
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        return jsonify({
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'exists': os.path.exists(app.config['UPLOAD_FOLDER']),
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- BLOK UNTUK MENJALANKAN SERVER ---
if __name__ == '__main__':
    # Print informasi penting saat server start
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Upload folder exists: {os.path.exists(app.config['UPLOAD_FOLDER'])}")
    app.run(debug=True, port=5001)