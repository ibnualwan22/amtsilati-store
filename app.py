import pymysql.cursors
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, send_from_directory
import os
import io
import requests
import functools
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from config import get_config
from datetime import datetime, date
from sqlalchemy import create_engine, text

# --- Inisialisasi Aplikasi Flask ---
app = Flask(__name__)

# Load konfigurasi berdasarkan environment
config = get_config()
app.config.from_object(config)

# Buat folder uploads jika belum ada
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    print(f"Created upload folder at: {app.config['UPLOAD_FOLDER']}")

# Buat folder instance jika belum ada (untuk database)
#instance_dir = os.path.dirname(app.config['DATABASE_PATH'])
#if not os.path.exists(instance_dir) and instance_dir != '':
#   os.makedirs(instance_dir)
#  print(f"Created instance folder at: {instance_dir}")

# Ekstensi file yang diperbolehkan
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Custom Filter Rupiah ---
@app.template_filter('rupiah')
def format_rupiah(value):
    """Format angka menjadi string dengan pemisah ribuan (titik)."""
    if value is None: return ""
    return f"{int(value):,}".replace(",", ".")

# --- Fungsi Koneksi Database ---
def get_db_connection():
    """Membuat koneksi ke database MySQL sesuai environment"""
    config = app.config
    conn = pymysql.connect(host=config['MYSQL_HOST'],
                             user=config['MYSQL_USER'],
                             password=config['MYSQL_PASSWORD'],
                             database=config['MYSQL_DB'],
                             port=config['MYSQL_PORT'],
                             cursorclass=pymysql.cursors.DictCursor, # Ini penting!
                             autocommit=True)
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
        return redirect('https://placehold.co/400x600/e2e8f0/4a5568?text=Gambar+Tidak+Ditemukan'), 404

# --- Rute Halaman Publik ---
@app.route('/')
def home():
    return redirect(url_for('shop_page'))

@app.route('/toko')
def shop_page():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM books ORDER BY name")
            books = cursor.fetchall()
    finally:
        conn.close()
    return render_template('shop.html', books=books)

@app.route('/toko/kitab/<int:book_id>')
def book_detail(book_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ganti placeholder '?' menjadi '%s' untuk PyMySQL
            cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
            book = cursor.fetchone()
            
            cursor.execute("SELECT * FROM books ORDER BY name")
            books = cursor.fetchall()
    finally:
        conn.close()
    if book is None: 
        return "Kitab tidak ditemukan.", 404
    return render_template('book_detail.html', book=book, books=books)

@app.route('/cek-ongkir')
def cek_ongkir_page():
    return render_template('cek_ongkir.html')

# --- Rute Halaman Login & Logout Admin ---
@app.route('/admin/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            # Gunakan 'with conn.cursor() as cursor:'
            with conn.cursor() as cursor:
                # Ganti placeholder '?' menjadi '%s'
                sql = "SELECT * FROM users WHERE username = %s"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
        finally:
            # Pastikan koneksi selalu ditutup
            conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau password salah!')
            
    return render_template('login.html')

@app.route('/admin/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Rute Halaman Admin (Struktur Modular Baru) ---
@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Menampilkan halaman dashboard utama."""
    return render_template('admin/dashboard.html')

@app.route('/admin/kitab')
@login_required
def admin_kitab():
    """Menampilkan halaman manajemen kitab."""
    return render_template('admin/kitab.html')

@app.route('/admin/kas')
@login_required
def admin_kas():
    """Menampilkan halaman rekap kas."""
    return render_template('admin/kas.html')

@app.route('/admin/pembeli')
@login_required
def admin_pembeli():
    """Menampilkan halaman data pembeli offline."""
    return render_template('admin/pembeli.html')

@app.route('/admin/penjualan/offline')
@login_required
def admin_penjualan_offline():
    """Menampilkan halaman input penjualan offline."""
    return render_template('admin/penjualan_offline.html')

@app.route('/admin/penjualan/online')
@login_required
def admin_penjualan_online():
    """Menampilkan halaman input penjualan online."""
    return render_template('admin/penjualan_online.html')

@app.route('/admin/transaksi')
@login_required
def admin_transaksi():
    """Menampilkan halaman riwayat semua transaksi."""
    return render_template('admin/riwayat_transaksi.html')

# ================== SEMUA API (ENDPOINT DATA) ==================

# --- API UNTUK MANAJEMEN KITAB (Dilindungi) ---
@app.route('/api/add-book', methods=['POST'])
@login_required
def add_book():
    # Mengambil data dari form
    try:
        name = request.form['name']
        price = request.form['price']
        availability = request.form['availability']
        link_ig = request.form.get('link_ig', '')
        link_wa = request.form.get('link_wa', '')
        link_shopee = request.form.get('link_shopee', '')
        link_tiktok = request.form.get('link_tiktok', '')
    except KeyError as e:
        return jsonify({'error': f'Form field {e} tidak ditemukan.'}), 400

    image_filename = None

    # Cek apakah ada file gambar yang diunggah
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            original_filename = secure_filename(image_file.filename)
            timestamp = str(int(time.time()))
            image_filename = f"{timestamp}_{original_filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(filepath)
            print(f"Image saved to: {filepath}")

    conn = get_db_connection()
    try:
        # Menggunakan 'with' untuk memastikan cursor tertutup otomatis
        with conn.cursor() as cursor:
            # Gunakan %s sebagai placeholder untuk PyMySQL
            sql = """
                INSERT INTO books 
                (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok, image_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok, image_filename))
        
        # Commit perubahan ke database
        conn.commit()
        return jsonify({'message': 'Kitab baru berhasil ditambahkan!'})

    except pymysql.IntegrityError:
        # Tangani error jika nama kitab sudah ada (UNIQUE constraint)
        return jsonify({'error': 'Nama kitab sudah ada.'}), 409
    except Exception as e:
        # Tangani error umum lainnya
        conn.rollback() # Batalkan perubahan jika ada error lain
        print(f"Error adding book: {str(e)}")
        return jsonify({'error': f'Terjadi kesalahan pada server: {str(e)}'}), 500
    finally:
        # Pastikan koneksi selalu ditutup
        conn.close()

@app.route('/api/update-book', methods=['POST'])
@login_required
def update_book():
    conn = get_db_connection()
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
        with conn.cursor() as cursor:
            sql = """UPDATE books SET 
                       name = %s, price = %s, availability = %s, link_ig = %s, link_wa = %s, 
                       link_shopee = %s, link_tiktok = %s, image_filename = %s
                       WHERE id = %s"""
            cursor.execute(sql, (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok, image_filename, book_id))
        conn.commit()
        return jsonify({'message': 'Data kitab berhasil diupdate!'})
    except Exception as e:
        conn.rollback()
        print(f"Error updating book: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/delete-book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil nama file gambar sebelum dihapus
            cursor.execute('SELECT image_filename FROM books WHERE id = %s', (book_id,))
            book = cursor.fetchone()
            
            # Hapus data dari database
            cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
        
        conn.commit()
        
        # Hapus file gambar jika ada (logika ini tetap sama)
        if book and book['image_filename']:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], book['image_filename'])
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Error deleting image file: {e}")
                    
        return jsonify({'message': 'Kitab berhasil dihapus.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/books/all', methods=['GET'])
@login_required
def get_all_books():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM books ORDER BY name')
            books = cursor.fetchall()
        return jsonify(books) # Tidak perlu [dict(row)...] lagi
    finally:
        conn.close()

@app.route('/api/books', methods=['GET'])
@login_required
def get_available_books():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM books WHERE availability = 'Tersedia' ORDER BY name")
            books = cursor.fetchall()
        return jsonify(books)
    finally:
        conn.close()

@app.route('/api/book/<int:book_id>', methods=['GET'])
@login_required
def get_book_details(book_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
            book = cursor.fetchone()
        if book is None:
            return jsonify({'error': 'Kitab tidak ditemukan'}), 404
        return jsonify(book)
    finally:
        conn.close()

# --- API UNTUK MANAJEMEN KITAB (Dilindungi) ---
@app.route('/api/import-books', methods=['POST'])
@login_required
def import_books():
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    try:
        df = pd.read_excel(io.BytesIO(file.read()), dtype=str).fillna('')
        
        conn = get_db_connection()
        imported = 0
        updated = 0
        
        with conn.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    name = row.get('Nama', '').strip()
                    if not name: continue
                    
                    price = float(row.get('Harga', 0))
                    availability = row.get('Ketersediaan', 'Tersedia').strip()
                    link_ig = row.get('Link Instagram', '').strip()
                    link_wa = row.get('Link WhatsApp', '').strip()
                    link_shopee = row.get('Link Shopee', '').strip()
                    link_tiktok = row.get('Link TikTok', '').strip()
                    
                    try:
                        # Coba insert dulu dengan placeholder %s
                        sql_insert = "INSERT INTO books (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql_insert, (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok))
                        imported += 1
                    except pymysql.IntegrityError:
                        # Jika gagal (nama sudah ada), update data
                        sql_update = "UPDATE books SET price = %s, availability = %s, link_ig = %s, link_wa = %s, link_shopee = %s, link_tiktok = %s WHERE name = %s"
                        cursor.execute(sql_update, (price, availability, link_ig, link_wa, link_shopee, link_tiktok, name))
                        updated += 1
                except Exception as e:
                    print(f"Error processing row {index}: {str(e)}")
                    continue
        
        conn.commit()
        return jsonify({'message': f'Import berhasil! Ditambah: {imported}, Diupdate: {updated}'})
        
    except Exception as e:
        return jsonify({'error': f"Error memproses file: {str(e)}"}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
# --- API UNTUK PEMBELI & IMPORT (Dilindungi) ---
@app.route('/api/offline-buyers', methods=['GET'])
@login_required
def get_offline_buyers():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM offline_buyers ORDER BY name')
            buyers = cursor.fetchall()
        return jsonify(buyers)
    finally:
        conn.close()

@app.route('/api/add-offline-sale', methods=['POST'])
@login_required
def add_offline_sale():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for item in data.get('items', []):
                cursor.execute('SELECT price FROM books WHERE id = %s', (item['book_id'],))
                book = cursor.fetchone()
                if not book:
                    raise ValueError(f"Kitab dengan ID {item['book_id']} tidak ditemukan")
                
                total_price = book['price'] * int(item['quantity'])
                sql = 'INSERT INTO offline_sales (buyer_id, book_id, quantity, total_price, payment_status) VALUES (%s, %s, %s, %s, %s)'
                cursor.execute(sql, (data.get('buyer_id'), item['book_id'], item['quantity'], total_price, data.get('payment_status', 'Lunas')))
        conn.commit()
        return jsonify({'message': 'Transaksi offline berhasil disimpan!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/add-online-sale', methods=['POST'])
@login_required
def add_online_sale():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Logika ini untuk form penjualan online multi-item
            if 'items' in data and data['items']:
                buyer_name = data['buyer_name']
                buyer_address = data['buyer_address']
                transfer_date = data['transfer_date']
                # Ambil total ongkir dari form
                shipping_cost = float(data.get('shipping_cost', 0))
                
                total_items = len(data['items'])
                for item in data['items']:
                    cursor.execute('SELECT price FROM books WHERE id = %s', (item['book_id'],))
                    book = cursor.fetchone()
                    if not book:
                        raise ValueError(f"Kitab dengan ID {item['book_id']} tidak ditemukan")

                    quantity = int(item.get('quantity', 1))
                    
                    # HITUNG ONGKIR PER ITEM (BAGIAN YANG HILANG/SALAH)
                    item_shipping_cost = shipping_cost / total_items if total_items > 0 else 0
                    
                    # Hitung total harga untuk item ini
                    total_price = (float(book['price']) * quantity) + item_shipping_cost
                    
                    # Simpan ke database
                    sql = """INSERT INTO online_sales 
                             (buyer_name, buyer_address, book_id, shipping_cost, total_price, transfer_date, quantity) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(sql, (buyer_name, buyer_address, item['book_id'], item_shipping_cost, total_price, transfer_date, quantity))
            else:
                # Fallback jika ada yang mengirim data dengan format lama (single item)
                # (Logika ini juga diperbaiki untuk konsistensi)
                cursor.execute('SELECT price FROM books WHERE id = %s', (data['book_id'],))
                book = cursor.fetchone()
                if not book:
                    return jsonify({'error': 'Kitab tidak ditemukan'}), 404
                
                quantity = int(data.get('quantity', 1))
                shipping_cost = float(data.get('shipping_cost', 0))
                total_price = (float(book['price']) * quantity) + shipping_cost

                sql = """INSERT INTO online_sales 
                         (buyer_name, buyer_address, book_id, shipping_cost, total_price, transfer_date, quantity) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (data['buyer_name'], data['buyer_address'], data['book_id'], shipping_cost, total_price, data['transfer_date'], quantity))

        conn.commit()
        return jsonify({'message': 'Rekap online berhasil ditambahkan!'})
    except Exception as e:
        conn.rollback()
        # Mengembalikan pesan error yang lebih spesifik ke frontend
        return jsonify({'error': f"Error memproses: {str(e)}"}), 500
    finally:
        if conn and conn.open:
            conn.close()

@app.route('/api/online-buyers', methods=['GET'])
@login_required
def get_online_buyers():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Mengambil nama unik dari tabel online_sales
            cursor.execute('SELECT DISTINCT buyer_name as name FROM online_sales ORDER BY name')
            buyers = cursor.fetchall()
        return jsonify(buyers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()


@app.route('/api/import-buyers', methods=['POST'])
@login_required
def import_buyers():
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    try:
        df = pd.read_excel(io.BytesIO(file.read()), dtype=str).fillna('')
        
        conn = get_db_connection()
        imported = 0
        updated = 0
        
        with conn.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    name = row.get('Nama', '').strip()
                    if not name: continue
                    
                    address = row.get('Alamat', '').strip()
                    
                    try:
                        # Coba insert dengan placeholder %s
                        cursor.execute('INSERT INTO offline_buyers (name, address) VALUES (%s, %s)', (name, address))
                        imported += 1
                    except pymysql.IntegrityError:
                        # Jika nama sudah ada, update alamatnya
                        cursor.execute('UPDATE offline_buyers SET address = %s WHERE name = %s', (address, name))
                        updated += 1
                except KeyError as e:
                    return jsonify({'error': f"Kolom '{e}' tidak ditemukan di file Excel."}), 400
        
        conn.commit()
        return jsonify({'message': f'Data berhasil diimpor! Ditambahkan: {imported}, Diupdate: {updated}'})
        
    except Exception as e:
        return jsonify({'error': f"Error memproses file: {str(e)}"}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
    
@app.route('/api/update-buyer', methods=['POST'])
@login_required
def update_buyer():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Gunakan cursor dan placeholder %s
            sql = "UPDATE offline_buyers SET name = %s, address = %s WHERE id = %s"
            cursor.execute(sql, (data['name'], data['address'], data['id']))
        conn.commit()
        return jsonify({'message': 'Data pembeli berhasil diupdate!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()

@app.route('/api/delete-buyer/<int:buyer_id>', methods=['POST'])
@login_required
def delete_buyer(buyer_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Cek transaksi terlebih dahulu
            cursor.execute('SELECT COUNT(*) as count FROM offline_sales WHERE buyer_id = %s', (buyer_id,))
            sales_count = cursor.fetchone()['count']
            
            if sales_count > 0:
                return jsonify({'error': f'Tidak bisa hapus. Pembeli punya {sales_count} transaksi.'}), 400
            
            # Jika tidak ada transaksi, hapus pembeli
            cursor.execute('DELETE FROM offline_buyers WHERE id = %s', (buyer_id,))
        conn.commit()
        return jsonify({'message': 'Pembeli berhasil dihapus.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()
    
@app.route('/api/delete-all-buyers', methods=['POST'])
@login_required
def delete_all_buyers():
    confirm = request.json.get('confirm')
    if confirm != 'DELETE_ALL_BUYERS':
        return jsonify({'error': 'Konfirmasi tidak valid'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Hapus semua transaksi dulu (mematikan foreign key check sementara)
            cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
            cursor.execute('DELETE FROM offline_sales')
            # Lalu hapus semua pembeli
            cursor.execute('DELETE FROM offline_buyers')
            cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
        conn.commit()
        return jsonify({'message': 'Semua data pembeli dan transaksi offline berhasil dihapus!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()
    

# --- API UNTUK REKAP PENJUALAN (Dilindungi) ---


@app.route('/api/recent-offline-sales')
@login_required
def get_all_offline_sales():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ganti strftime menjadi DATE_FORMAT
            query = """
            SELECT os.id, ob.name as buyer_name, ob.address, b.name as book_name, 
                   os.quantity, os.total_price, os.payment_status,
                   DATE_FORMAT(os.sale_date, '%%d-%%m-%%Y %%H:%%i') as sale_date_formatted
            FROM offline_sales os
            JOIN offline_buyers ob ON os.buyer_id = ob.id
            JOIN books b ON os.book_id = b.id
            WHERE 1=1
            """
            
            params = []
            # ... (logika filter tetap sama) ...
            payment_status = request.args.get('payment_status')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            if payment_status and payment_status != 'all':
                query += " AND os.payment_status = %s"
                params.append(payment_status)
            if start_date:
                query += " AND DATE(os.sale_date) >= %s"
                params.append(start_date)
            if end_date:
                query += " AND DATE(os.sale_date) <= %s"
                params.append(end_date)
            
            query += " ORDER BY os.id DESC"
            
            cursor.execute(query, params)
            sales = cursor.fetchall()
            return jsonify(sales)
    finally:
        conn.close()
# TAMBAHKAN ENDPOINT INI DI app.py setelah endpoint transaksi yang sudah ada

@app.route('/api/recent-online-sales')
@login_required
def get_all_online_sales():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ganti strftime menjadi DATE_FORMAT
            query = """
            SELECT 
                os.id, os.buyer_name, os.buyer_address, b.name as book_name, os.shipping_cost, 
                os.total_price, os.quantity,
                DATE_FORMAT(os.sale_date, '%%d-%%m-%%Y %%H:%%i') as sale_date_formatted,
                DATE_FORMAT(os.transfer_date, '%%d-%%m-%%Y') as transfer_date_formatted
            FROM online_sales os
            JOIN books b ON os.book_id = b.id
            WHERE 1=1
            """
            
            params = []
            # ... (logika filter tetap sama) ...
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            if start_date:
                query += " AND DATE(os.transfer_date) >= %s"
                params.append(start_date)
            if end_date:
                query += " AND DATE(os.transfer_date) <= %s"
                params.append(end_date)
            
            query += " ORDER BY os.id DESC"
            
            cursor.execute(query, params)
            sales = cursor.fetchall()
            return jsonify(sales)
    finally:
        conn.close()

# --- API UNTUK EDIT/HAPUS TRANSAKSI OFFLINE ---
@app.route('/api/update-offline-sale', methods=['POST'])
@login_required
def update_offline_sale():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT price FROM books WHERE id = %s', (data['book_id'],))
            book = cursor.fetchone()
            if not book:
                return jsonify({'error': 'Kitab tidak ditemukan'}), 404
            
            total_price = float(book['price']) * int(data['quantity'])
            
            sql = '''
                UPDATE offline_sales 
                SET buyer_id = %s, book_id = %s, quantity = %s, total_price = %s, payment_status = %s
                WHERE id = %s
            '''
            cursor.execute(sql, (data['buyer_id'], data['book_id'], data['quantity'], total_price, data['payment_status'], data['id']))
        conn.commit()
        return jsonify({'message': 'Transaksi offline berhasil diupdate!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/delete-offline-sale/<int:sale_id>', methods=['POST'])
@login_required
def delete_offline_sale(sale_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM offline_sales WHERE id = %s', (sale_id,))
        conn.commit()
        return jsonify({'message': 'Transaksi offline berhasil dihapus!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/get-offline-sale/<int:sale_id>', methods=['GET'])
@login_required
def get_offline_sale(sale_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT os.*, ob.name as buyer_name, b.name as book_name
                FROM offline_sales os
                JOIN offline_buyers ob ON os.buyer_id = ob.id
                JOIN books b ON os.book_id = b.id
                WHERE os.id = %s
            ''', (sale_id,))
            sale = cursor.fetchone()
            if not sale:
                return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
            return jsonify(sale)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- API UNTUK EDIT/HAPUS TRANSAKSI ONLINE ---
@app.route('/api/update-online-sale', methods=['POST'])
@login_required
def update_online_sale():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT price FROM books WHERE id = %s', (data['book_id'],))
            book = cursor.fetchone()
            if not book:
                return jsonify({'error': 'Kitab tidak ditemukan'}), 404

            total_price = (float(book['price']) * int(data['quantity'])) + float(data['shipping_cost'])
            
            sql = '''
                UPDATE online_sales 
                SET buyer_name = %s, buyer_address = %s, book_id = %s, 
                    quantity = %s, shipping_cost = %s, total_price = %s, transfer_date = %s
                WHERE id = %s
            '''
            cursor.execute(sql, (data['buyer_name'], data['buyer_address'], data['book_id'], data['quantity'], 
                                 data['shipping_cost'], total_price, data['transfer_date'], data['id']))
        conn.commit()
        return jsonify({'message': 'Transaksi online berhasil diupdate!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/delete-online-sale/<int:sale_id>', methods=['POST'])
@login_required
def delete_online_sale(sale_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM online_sales WHERE id = %s', (sale_id,))
        conn.commit()
        return jsonify({'message': 'Transaksi online berhasil dihapus!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/get-online-sale/<int:sale_id>', methods=['GET'])
@login_required
def get_online_sale(sale_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ganti strftime menjadi DATE_FORMAT
            cursor.execute('''
                SELECT os.*, b.name as book_name,
                       DATE_FORMAT(os.transfer_date, '%%Y-%%m-%%d') as transfer_date_formatted
                FROM online_sales os
                JOIN books b ON os.book_id = b.id
                WHERE os.id = %s
            ''', (sale_id,))
            sale = cursor.fetchone()
            if not sale:
                return jsonify({'error': 'Transaksi tidak ditemukan'}), 404
            return jsonify(sale)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- API UNTUK EXPORT EXCEL (Dilindungi) ---
@app.route('/api/export-offline-sales')
@login_required
def export_offline():
    try:
        # Membuat koneksi menggunakan SQLAlchemy
        config = app.config
        db_uri = f"mysql+pymysql://{config['MYSQL_USER']}:{config['MYSQL_PASSWORD']}@{config['MYSQL_HOST']}:{config['MYSQL_PORT']}/{config['MYSQL_DB']}"
        engine = create_engine(db_uri)

        query = """
        SELECT DATE_FORMAT(os.sale_date, '%%d-%%m-%%Y %%H:%%i') as 'Tanggal Transaksi', 
               ob.name as 'Nama Pembeli', 
               ob.address as 'Alamat', 
               b.name as 'Nama Kitab', 
               os.quantity as 'Jumlah', 
               b.price as 'Harga Satuan', 
               os.total_price as 'Total Harga',
               IFNULL(os.payment_status, 'Lunas') as 'Status Pembayaran'
        FROM offline_sales os
        JOIN offline_buyers ob ON os.buyer_id = ob.id
        JOIN books b ON os.book_id = b.id
        WHERE 1=1
        """
        
        params = []
        payment_status = request.args.get('payment_status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if payment_status and payment_status != 'all':
            query += " AND os.payment_status = %(payment_status)s"
            params.append({'payment_status': payment_status})
        if start_date:
            query += " AND DATE(os.sale_date) >= %(start_date)s"
            params.append({'start_date': start_date})
        if end_date:
            query += " AND DATE(os.sale_date) <= %(end_date)s"
            params.append({'end_date': end_date})
        
        query += " ORDER BY os.id DESC"
        
        # Menggabungkan semua parameter menjadi satu dictionary
        final_params = {k: v for d in params for k, v in d.items()}

        df = pd.read_sql_query(query, engine, params=final_params if final_params else None)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Rekap Offline')
            worksheet = writer.sheets['Rekap Offline']
            worksheet.column_dimensions['A'].width = 18
            worksheet.column_dimensions['B'].width = 25
            worksheet.column_dimensions['C'].width = 30
            worksheet.column_dimensions['D'].width = 25
            worksheet.column_dimensions['E'].width = 10
            worksheet.column_dimensions['F'].width = 15
            worksheet.column_dimensions['G'].width = 15
            worksheet.column_dimensions['H'].width = 18
            
        output.seek(0)
        
        filename_parts = ['rekap_offline', datetime.now().strftime('%Y%m%d')]
        filename = '_'.join(filename_parts) + '.xlsx'
        
        return send_file(output, download_name=filename, as_attachment=True)

    except Exception as e:
        print(f"Error exporting offline sales: {e}")
        return "Gagal mengekspor data", 500
# 1. PERBAIKAN DI app.py - Ganti fungsi import_offline() yang ada dengan ini:

# UPDATE endpoint /api/import-offline-sales di app.py
@app.route('/api/import-offline-sales', methods=['POST'])
@login_required
def import_offline_sales():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang di-upload'}), 400
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Format file harus Excel'}), 400

    try:
        df = pd.read_excel(file)
        conn = get_db_connection()
        imported = 0
        skipped = 0
        warnings = []
        
        with conn.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    nama_pembeli = str(row['Nama Pembeli']).strip()
                    nama_kitab = str(row['Nama Kitab']).strip()
                    jumlah = int(row['Jumlah'])
                    payment_status = str(row.get('Status Pembayaran', 'Lunas')).strip()

                    # Cari atau buat pembeli
                    cursor.execute('SELECT id FROM offline_buyers WHERE name = %s', (nama_pembeli,))
                    buyer = cursor.fetchone()
                    if not buyer:
                        alamat = str(row.get('Alamat', '')).strip()
                        cursor.execute('INSERT INTO offline_buyers (name, address) VALUES (%s, %s)', (nama_pembeli, alamat))
                        buyer_id = cursor.lastrowid
                    else:
                        buyer_id = buyer['id']
                    
                    # Cari kitab
                    cursor.execute('SELECT id, price FROM books WHERE name = %s', (nama_kitab,))
                    book = cursor.fetchone()
                    if not book:
                        warnings.append(f"Baris {index+2}: Kitab '{nama_kitab}' tidak ditemukan")
                        skipped += 1
                        continue
                    
                    total_price = book['price'] * jumlah
                    sql = 'INSERT INTO offline_sales (buyer_id, book_id, quantity, total_price, payment_status) VALUES (%s, %s, %s, %s, %s)'
                    cursor.execute(sql, (buyer_id, book['id'], jumlah, total_price, payment_status))
                    imported += 1
                except Exception as e:
                    warnings.append(f"Baris {index+2}: {str(e)}")
                    skipped += 1
                    continue
        
        conn.commit()
        # ... (Logika pesan response tetap sama) ...
        message = f'Import selesai! Berhasil: {imported}, Dilewati: {skipped}'
        return jsonify({'message': message, 'warnings': warnings})

    except Exception as e:
        return jsonify({'error': f'Error memproses file: {str(e)}'}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

# 2. TAMBAHKAN fungsi baru untuk import online sales di app.py:

@app.route('/api/import-online-sales', methods=['POST'])
@login_required
def import_online_sales():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang di-upload'}), 400
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Format file harus Excel'}), 400

    try:
        df = pd.read_excel(file)
        conn = get_db_connection()
        imported = 0
        skipped = 0
        warnings = []
        
        with conn.cursor() as cursor:
            for index, row in df.iterrows():
                try:
                    nama_pembeli = str(row['Nama Pembeli']).strip()
                    nama_kitab = str(row['Nama Kitab']).strip()
                    jumlah = int(row['Jumlah'])
                    alamat_kirim = str(row.get('Alamat Kirim', '')).strip()
                    ongkir = float(row.get('Ongkir', 15000))
                    
                    # ... (logika handle tanggal transfer tetap sama) ...
                    tanggal_transfer = row.get('Tanggal Transfer', pd.Timestamp.now().strftime('%Y-%m-%d'))
                    if pd.notna(tanggal_transfer):
                        tanggal_transfer = pd.to_datetime(tanggal_transfer).strftime('%Y-%m-%d')
                    
                    # Cari kitab
                    cursor.execute('SELECT id, price FROM books WHERE name = %s', (nama_kitab,))
                    book = cursor.fetchone()
                    if not book:
                        warnings.append(f"Baris {index+2}: Kitab '{nama_kitab}' tidak ditemukan")
                        skipped += 1
                        continue
                    
                    total_price = (book['price'] * jumlah) + ongkir
                    sql = 'INSERT INTO online_sales (buyer_name, buyer_address, book_id, quantity, shipping_cost, total_price, transfer_date) VALUES (%s, %s, %s, %s, %s, %s, %s)'
                    cursor.execute(sql, (nama_pembeli, alamat_kirim, book['id'], jumlah, ongkir, total_price, tanggal_transfer))
                    imported += 1
                except Exception as e:
                    warnings.append(f"Baris {index+2}: {str(e)}")
                    skipped += 1
                    continue
        
        conn.commit()
        # ... (Logika pesan response tetap sama) ...
        message = f'Import selesai! Berhasil: {imported}, Dilewati: {skipped}'
        return jsonify({'message': message, 'warnings': warnings})

    except Exception as e:
        return jsonify({'error': f'Error memproses file: {str(e)}'}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()


# app.py

@app.route('/api/export-online-sales')
@login_required
def export_online():
    try:
        # Membuat koneksi menggunakan SQLAlchemy
        config = app.config
        db_uri = f"mysql+pymysql://{config['MYSQL_USER']}:{config['MYSQL_PASSWORD']}@{config['MYSQL_HOST']}:{config['MYSQL_PORT']}/{config['MYSQL_DB']}"
        engine = create_engine(db_uri)

        query = """
        SELECT 
            DATE_FORMAT(os.sale_date, '%%d-%%m-%%Y %%H:%%i') as 'Tanggal Transaksi', 
            DATE_FORMAT(os.transfer_date, '%%d-%%m-%%Y') as 'Tanggal Transfer',
            os.buyer_name as 'Nama Pembeli', 
            os.buyer_address as 'Alamat Pengiriman', 
            b.name as 'Nama Kitab', 
            os.quantity as 'Jumlah',
            b.price as 'Harga Kitab', 
            os.shipping_cost as 'Ongkir', 
            os.total_price as 'Total Harga'
        FROM online_sales os
        JOIN books b ON os.book_id = b.id
        WHERE 1=1
        """
        params = []
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            query += " AND DATE(os.transfer_date) >= %(start_date)s"
            params.append({'start_date': start_date})
        if end_date:
            query += " AND DATE(os.transfer_date) <= %(end_date)s"
            params.append({'end_date': end_date})
        
        query += " ORDER BY os.id DESC"
        
        final_params = {k: v for d in params for k, v in d.items()}

        df = pd.read_sql_query(query, engine, params=final_params if final_params else None)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Rekap Online')
            worksheet = writer.sheets['Rekap Online']
            worksheet.column_dimensions['A'].width = 18
            worksheet.column_dimensions['B'].width = 18
            worksheet.column_dimensions['C'].width = 25
            worksheet.column_dimensions['D'].width = 35
            worksheet.column_dimensions['E'].width = 25
            worksheet.column_dimensions['F'].width = 10
            worksheet.column_dimensions['G'].width = 15
            worksheet.column_dimensions['H'].width = 15
            worksheet.column_dimensions['I'].width = 15
            
        output.seek(0)
        
        filename = f"rekap_online_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(output, download_name=filename, as_attachment=True)

    except Exception as e:
        print(f"Error exporting online sales: {e}")
        return "Gagal mengekspor data", 500

# --- API UNTUK CASH RECORDS (Dilindungi) ---
@app.route('/api/cash-records', methods=['GET'])
@login_required
def get_cash_records():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            record_type = request.args.get('type')
            
            query = "SELECT *, DATE_FORMAT(record_date, '%%d-%%m-%%Y') as record_date_formatted FROM cash_records WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND record_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND record_date <= %s"
                params.append(end_date)
            if record_type:
                query += " AND type = %s"
                params.append(record_type)
            query += " ORDER BY record_date DESC, id DESC"
            cursor.execute(query, params)
            records = cursor.fetchall()
            
            # Logika query summary
            summary_query = "SELECT type, COALESCE(SUM(amount), 0) as total FROM cash_records WHERE 1=1"
            summary_params = []
            if start_date:
                summary_query += " AND record_date >= %s"
                summary_params.append(start_date)
            if end_date:
                summary_query += " AND record_date <= %s"
                summary_params.append(end_date)
            summary_query += " GROUP BY type"
            cursor.execute(summary_query, summary_params)
            summary_results = cursor.fetchall()

            total_debit = next((item['total'] for item in summary_results if item['type'] == 'debit'), 0)
            total_kredit = next((item['total'] for item in summary_results if item['type'] == 'kredit'), 0)
            total_kas = total_debit - total_kredit

            return jsonify({
                'records': records,
                'summary': {
                    'total_debit': float(total_debit),
                    'total_kredit': float(total_kredit),
                    'total_kas': float(total_kas)
                }
            })
    except Exception as e:
        print(f"Error getting cash records: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()

@app.route('/api/add-cash-record', methods=['POST'])
@login_required
def add_cash_record():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO cash_records (type, amount, description, category, record_date) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (data['type'], data['amount'], data['description'], data.get('category', ''), data['record_date']))
        conn.commit()
        return jsonify({'message': 'Catatan kas berhasil ditambahkan!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()

@app.route('/api/update-cash-record', methods=['POST'])
@login_required
def update_cash_record():
    data = request.json
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "UPDATE cash_records SET type = %s, amount = %s, description = %s, category = %s, record_date = %s WHERE id = %s"
            cursor.execute(sql, (data['type'], data['amount'], data['description'], data.get('category', ''), data['record_date'], data['id']))
        conn.commit()
        return jsonify({'message': 'Catatan kas berhasil diupdate!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()

@app.route('/api/delete-cash-record/<int:record_id>', methods=['POST'])
@login_required
def delete_cash_record(record_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM cash_records WHERE id = %s', (record_id,))
        conn.commit()
        return jsonify({'message': 'Catatan kas berhasil dihapus!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.open:
            conn.close()

@app.route('/api/export-cash-records')
@login_required
def export_cash_records():
    try:
        # Membuat koneksi menggunakan SQLAlchemy
        config = app.config
        db_uri = f"mysql+pymysql://{config['MYSQL_USER']}:{config['MYSQL_PASSWORD']}@{config['MYSQL_HOST']}:{config['MYSQL_PORT']}/{config['MYSQL_DB']}"
        engine = create_engine(db_uri)

        query = """
        SELECT 
            DATE_FORMAT(record_date, '%%d-%%m-%%Y') as 'Tanggal',
            CASE 
                WHEN type = 'debit' THEN 'Debit (Kas Masuk)'
                ELSE 'Kredit (Kas Keluar)'
            END as 'Jenis Transaksi',
            description as 'Keterangan',
            category as 'Kategori',
            amount as 'Jumlah'
        FROM cash_records
        ORDER BY record_date DESC, id DESC
        """
        df = pd.read_sql_query(query, engine)
        
        # Gunakan koneksi dari engine untuk query summary
        with engine.connect() as connection:
            total_debit_result = connection.execute(text("SELECT COALESCE(SUM(amount), 0) FROM cash_records WHERE type = 'debit'")).scalar_one()
            total_kredit_result = connection.execute(text("SELECT COALESCE(SUM(amount), 0) FROM cash_records WHERE type = 'kredit'")).scalar_one()
            
        total_debit = float(total_debit_result)
        total_kredit = float(total_kredit_result)
        saldo_akhir = total_debit - total_kredit
        
        summary_df = pd.DataFrame([
            {'Tanggal': '', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': ''},
            {'Tanggal': 'RINGKASAN', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': ''},
            {'Tanggal': 'Total Debit', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': total_debit},
            {'Tanggal': 'Total Kredit', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': total_kredit},
            {'Tanggal': 'Saldo Akhir', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': saldo_akhir}
        ])
        
        final_df = pd.concat([df, summary_df], ignore_index=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Rekap Kas')
            worksheet = writer.sheets['Rekap Kas']
            worksheet.column_dimensions['A'].width = 15
            worksheet.column_dimensions['B'].width = 20
            worksheet.column_dimensions['C'].width = 40
            worksheet.column_dimensions['D'].width = 15
            worksheet.column_dimensions['E'].width = 15
            
        output.seek(0)
        
        filename = f'rekap_kas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(output, download_name=filename, as_attachment=True)
        
    except Exception as e:
        print(f"Error exporting cash records: {str(e)}")
        return "Terjadi kesalahan saat membuat file export.", 500

# --- API Publik untuk Ongkir ---
@app.route('/api/cari-area', methods=['GET'])
def search_areas():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    headers = {'Authorization': f'Bearer {app.config["BITESHIP_API_KEY"]}'}
    url = f"{app.config['BITESHIP_BASE_URL']}/v1/maps/areas?countries=ID&input={query}&type=single"
    
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
        'Authorization': f'Bearer {app.config["BITESHIP_API_KEY"]}',
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
        response = requests.post(f"{app.config['BITESHIP_BASE_URL']}/v1/rates/couriers", headers=headers, json=payload)
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

# app.py

@app.route('/debug/check-config')
@login_required
def check_config():
    """Route untuk debugging - cek konfigurasi yang digunakan"""
    config = app.config
    return jsonify({
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'upload_folder': config.get('UPLOAD_FOLDER'),
        'debug': config.get('DEBUG'),
        'testing': config.get('TESTING'),
        'mysql_config': {
            'host': config.get('MYSQL_HOST'),
            'user': config.get('MYSQL_USER'),
            'database': config.get('MYSQL_DB'),
            'port': config.get('MYSQL_PORT')
        }
    })

