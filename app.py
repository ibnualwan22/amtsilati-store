import sqlite3
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
instance_dir = os.path.dirname(app.config['DATABASE_PATH'])
if not os.path.exists(instance_dir) and instance_dir != '':
    os.makedirs(instance_dir)
    print(f"Created instance folder at: {instance_dir}")

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
    """Membuat koneksi ke database sesuai environment"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
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
        # Baca file Excel
        file_content = file.read()
        df = pd.read_excel(io.BytesIO(file_content), dtype=str).fillna('')
        
        conn = get_db_connection()
        imported = 0
        updated = 0
        
        # Kolom yang diharapkan
        required_columns = ['Nama', 'Harga']
        
        # Cek kolom yang ada
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            conn.close()
            return jsonify({'error': f"Kolom berikut tidak ditemukan: {', '.join(missing_columns)}"}), 400
        
        for index, row in df.iterrows():
            try:
                name = row.get('Nama', '').strip()
                price = float(row.get('Harga', 0))
                availability = row.get('Ketersediaan', 'Tersedia').strip()
                link_ig = row.get('Link Instagram', '').strip()
                link_wa = row.get('Link WhatsApp', '').strip()
                link_shopee = row.get('Link Shopee', '').strip()
                link_tiktok = row.get('Link TikTok', '').strip()
                
                if not name or price <= 0:
                    continue
                
                # Coba insert dulu
                try:
                    conn.execute(
                        """INSERT INTO books (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok)
                    )
                    imported += 1
                except sqlite3.IntegrityError:
                    # Jika gagal karena nama sudah ada, update
                    conn.execute(
                        """UPDATE books SET price = ?, availability = ?, link_ig = ?, 
                           link_wa = ?, link_shopee = ?, link_tiktok = ?
                           WHERE name = ?""",
                        (price, availability, link_ig, link_wa, link_shopee, link_tiktok, name)
                    )
                    updated += 1
                    
            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'Import berhasil! Ditambah: {imported}, Diupdate: {updated}'})
        
    except Exception as e:
        return jsonify({'error': f"Error memproses file: {str(e)}"}), 500

@app.route('/api/add-book', methods=['POST'])

# --- API UNTUK PEMBELI & IMPORT (Dilindungi) ---
@app.route('/api/offline-buyers', methods=['GET'])
@login_required
def get_offline_buyers():
    conn = get_db_connection()
    buyers = conn.execute('SELECT * FROM offline_buyers ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(row) for row in buyers])

@app.route('/api/online-buyers', methods=['GET'])
@login_required
def get_online_buyers():
    conn = get_db_connection()
    buyers = conn.execute('SELECT * FROM online_buyers ORDER BY name').fetchall()
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

    try:
        # Baca file langsung dari memory
        file_content = file.read()
        
        NAMA_KOLOM = 'Nama'
        ALAMAT_KOLOM = 'Alamat'
        
        df = pd.read_excel(io.BytesIO(file_content), dtype=str).fillna('')
        
        conn = get_db_connection()
        imported = 0
        updated = 0
        
        for index, row in df.iterrows():
            try:
                name = row.get(NAMA_KOLOM, '')
                address = row.get(ALAMAT_KOLOM, '')
                
                if not name:  # Skip jika nama kosong
                    continue
                    
                try:
                    conn.execute('INSERT INTO offline_buyers (name, address) VALUES (?, ?)', 
                               (name, address))
                    imported += 1
                except sqlite3.IntegrityError:
                    conn.execute('UPDATE offline_buyers SET address = ? WHERE name = ?', 
                               (address, name))
                    updated += 1
                    
            except KeyError as e:
                conn.close()
                return jsonify({'error': f"Kolom '{e}' tidak ditemukan di file Excel."}), 400
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': f'Data berhasil diimpor! Ditambahkan: {imported}, Diupdate: {updated}'})
        
    except Exception as e:
        return jsonify({'error': f"Error memproses file: {str(e)}"}), 500
    
@app.route('/api/update-buyer', methods=['POST'])
@login_required
def update_buyer():
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute('UPDATE offline_buyers SET name = ?, address = ? WHERE id = ?', 
                    (data['name'], data['address'], data['id']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Data pembeli berhasil diupdate!'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-buyer/<int:buyer_id>', methods=['POST'])
@login_required
def delete_buyer(buyer_id):
    conn = get_db_connection()
    try:
        # Cek transaksi
        sales = conn.execute('SELECT COUNT(*) FROM offline_sales WHERE buyer_id = ?', 
                           (buyer_id,)).fetchone()[0]
        if sales > 0:
            return jsonify({'error': f'Tidak bisa hapus. Pembeli punya {sales} transaksi.'}), 400
        
        conn.execute('DELETE FROM offline_buyers WHERE id = ?', (buyer_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Pembeli berhasil dihapus.'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/delete-all-buyers', methods=['POST'])
@login_required
def delete_all_buyers():
    # Extra confirmation
    confirm = request.json.get('confirm')
    if confirm != 'DELETE_ALL_BUYERS':
        return jsonify({'error': 'Konfirmasi tidak valid'}), 400
    
    conn = get_db_connection()
    try:
        # Hapus semua transaksi dulu
        conn.execute('DELETE FROM offline_sales')
        # Lalu hapus semua pembeli
        conn.execute('DELETE FROM offline_buyers')
        conn.commit()
        conn.close()
        return jsonify({'message': 'Semua data pembeli berhasil dihapus!'})
    except Exception as e:
        conn.close()
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

@app.route('/api/add-online-sale', methods=['POST'])
@login_required
def add_online_sale():
    data = request.json
    try:
        conn = get_db_connection()
        
        # Check if this is multi-item sale
        if 'items' in data:
            # Multi-item sale
            buyer_name = data['buyer_name']
            buyer_address = data['buyer_address']
            transfer_date = data['transfer_date']
            shipping_cost = data.get('shipping_cost', 15000)
            
            # Calculate total items to split shipping cost
            total_items = len(data['items'])
            
            # Process each item
            for item in data['items']:
                book = conn.execute('SELECT price FROM books WHERE id = ?', (item['book_id'],)).fetchone()
                if not book:
                    conn.close()
                    return jsonify({'error': f'Kitab dengan ID {item["book_id"]} tidak ditemukan'}), 404
                
                quantity = int(item.get('quantity', 1))
                # Split shipping cost proportionally among items
                item_shipping = shipping_cost / total_items
                total_price = (book['price'] * quantity) + item_shipping
                
                conn.execute(
                    'INSERT INTO online_sales (buyer_name, buyer_address, book_id, shipping_cost, total_price, transfer_date, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (buyer_name, buyer_address, item['book_id'], item_shipping, total_price, transfer_date, quantity)
                )
        else:
            # Single item sale (backward compatibility)
            book = conn.execute('SELECT price FROM books WHERE id = ?', (data['book_id'],)).fetchone()
            if not book:
                conn.close()
                return jsonify({'error': 'Kitab tidak ditemukan'}), 404
            
            quantity = int(data.get('quantity', 1))
            shipping_cost = data.get('shipping_cost', 15000)
            total_price = (book['price'] * quantity) + shipping_cost

            conn.execute(
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
    SELECT os.id, ob.name as buyer_name, ob.address, b.name as book_name, 
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
    # Update query - HAPUS ob.dormitory
    query = """
    SELECT strftime('%d-%m-%Y %H:%M', os.sale_date) as 'Tanggal Transaksi', 
           ob.name as 'Nama Pembeli', 
           ob.address as 'Alamat', 
           b.name as 'Nama Kitab', 
           os.quantity as 'Jumlah', 
           b.price as 'Harga Satuan', 
           os.total_price as 'Total Harga'
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

# 1. PERBAIKAN DI app.py - Ganti fungsi import_offline() yang ada dengan ini:

@app.route('/api/import-offline-sales', methods=['POST'])
@login_required
def import_offline_sales():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang di-upload'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'File tidak dipilih'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'File harus berformat Excel (.xlsx atau .xls)'}), 400
    
    try:
        # Baca file Excel
        df = pd.read_excel(file)
        
        # Pastikan kolom yang dibutuhkan ada
        required_columns = ['Nama Pembeli', 'Nama Kitab', 'Jumlah']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': f'File harus memiliki kolom: {", ".join(required_columns)}'}), 400
        
        conn = get_db_connection()
        imported = 0
        skipped = 0
        warnings = []
        
        for index, row in df.iterrows():
            try:
                nama_pembeli = str(row['Nama Pembeli']).strip()
                nama_kitab = str(row['Nama Kitab']).strip()
                jumlah = int(row['Jumlah'])
                
                if not nama_pembeli or not nama_kitab or jumlah <= 0:
                    skipped += 1
                    continue
                
                # Cari atau buat pembeli
                buyer = conn.execute('SELECT id FROM offline_buyers WHERE name = ?', (nama_pembeli,)).fetchone()
                if not buyer:
                    # Tambah pembeli baru
                    cursor = conn.execute('INSERT INTO offline_buyers (name, address) VALUES (?, ?)', 
                                         (nama_pembeli, ''))
                    buyer_id = cursor.lastrowid
                else:
                    buyer_id = buyer['id']
                
                # Cari kitab
                book = conn.execute('SELECT id, price FROM books WHERE name = ?', (nama_kitab,)).fetchone()
                if not book:
                    warnings.append(f"Baris {index+2}: Kitab '{nama_kitab}' tidak ditemukan")
                    skipped += 1
                    continue
                
                # Hitung total harga
                total_price = book['price'] * jumlah
                
                # Insert transaksi
                conn.execute(
                    'INSERT INTO offline_sales (buyer_id, book_id, quantity, total_price) VALUES (?, ?, ?, ?)',
                    (buyer_id, book['id'], jumlah, total_price)
                )
                imported += 1
                
            except Exception as e:
                warnings.append(f"Baris {index+2}: {str(e)}")
                skipped += 1
                continue
        
        conn.commit()
        conn.close()
        
        message = f'Import selesai! Berhasil: {imported} transaksi'
        if skipped > 0:
            message += f', Dilewati: {skipped} baris'
        
        return jsonify({
            'message': message,
            'imported': imported,
            'skipped': skipped,
            'warnings': warnings
        })
        
    except Exception as e:
        return jsonify({'error': f'Error memproses file: {str(e)}'}), 500


# 2. TAMBAHKAN fungsi baru untuk import online sales di app.py:

@app.route('/api/import-online-sales', methods=['POST'])
@login_required
def import_online_sales():
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang di-upload'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'File tidak dipilih'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'File harus berformat Excel (.xlsx atau .xls)'}), 400
    
    try:
        # Baca file Excel
        df = pd.read_excel(file)
        
        # Kolom yang dibutuhkan
        required_columns = ['Nama Pembeli', 'Alamat Kirim', 'Nama Kitab', 'Jumlah', 'Ongkir', 'Tanggal Transfer']
        
        # Cek kolom minimal (Nama Pembeli, Nama Kitab, Jumlah)
        minimal_columns = ['Nama Pembeli', 'Nama Kitab', 'Jumlah']
        if not all(col in df.columns for col in minimal_columns):
            return jsonify({'error': f'File minimal harus memiliki kolom: {", ".join(minimal_columns)}'}), 400
        
        conn = get_db_connection()
        imported = 0
        skipped = 0
        warnings = []
        
        for index, row in df.iterrows():
            try:
                nama_pembeli = str(row['Nama Pembeli']).strip()
                nama_kitab = str(row['Nama Kitab']).strip()
                jumlah = int(row['Jumlah'])
                
                # Kolom opsional dengan default value
                alamat_kirim = str(row.get('Alamat Kirim', '')).strip()
                ongkir = float(row.get('Ongkir', 15000))  # Default ongkir 15000
                
                # Handle tanggal transfer
                tanggal_transfer = row.get('Tanggal Transfer', None)
                if pd.notna(tanggal_transfer):
                    # Jika ada tanggal, konversi ke format yang sesuai
                    if isinstance(tanggal_transfer, str):
                        # Coba parse berbagai format tanggal
                        from datetime import datetime
                        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                            try:
                                tanggal_transfer = datetime.strptime(tanggal_transfer, fmt).strftime('%Y-%m-%d')
                                break
                            except:
                                continue
                    else:
                        # Jika sudah datetime object
                        tanggal_transfer = tanggal_transfer.strftime('%Y-%m-%d')
                else:
                    # Jika tidak ada tanggal, gunakan hari ini
                    from datetime import date
                    tanggal_transfer = date.today().strftime('%Y-%m-%d')
                
                if not nama_pembeli or not nama_kitab or jumlah <= 0:
                    skipped += 1
                    continue
                
                # Cari kitab
                book = conn.execute('SELECT id, price FROM books WHERE name = ?', (nama_kitab,)).fetchone()
                if not book:
                    warnings.append(f"Baris {index+2}: Kitab '{nama_kitab}' tidak ditemukan")
                    skipped += 1
                    continue
                
                # Hitung total harga
                total_price = (book['price'] * jumlah) + ongkir
                
                # Insert transaksi online
                conn.execute(
                    '''INSERT INTO online_sales 
                       (buyer_name, buyer_address, book_id, quantity, shipping_cost, total_price, transfer_date) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (nama_pembeli, alamat_kirim, book['id'], jumlah, ongkir, total_price, tanggal_transfer)
                )
                imported += 1
                
            except Exception as e:
                warnings.append(f"Baris {index+2}: {str(e)}")
                skipped += 1
                continue
        
        conn.commit()
        conn.close()
        
        message = f'Import selesai! Berhasil: {imported} transaksi'
        if skipped > 0:
            message += f', Dilewati: {skipped} baris'
        
        return jsonify({
            'message': message,
            'imported': imported,
            'skipped': skipped,
            'warnings': warnings
        })
        
    except Exception as e:
        return jsonify({'error': f'Error memproses file: {str(e)}'}), 500




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

# TAMBAHKAN ENDPOINT INI DI app.py setelah endpoint yang sudah ada

# --- API UNTUK CASH RECORDS (Dilindungi) ---
@app.route('/api/cash-records', methods=['GET'])
@login_required
def get_cash_records():
    try:
        conn = get_db_connection()
        
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        record_type = request.args.get('type')
        
        # Base query
        query = "SELECT * FROM cash_records WHERE 1=1"
        params = []
        
        # Add filters
        if start_date:
            query += " AND date(record_date) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(record_date) <= date(?)"
            params.append(end_date)
        if record_type:
            query += " AND type = ?"
            params.append(record_type)
            
        query += " ORDER BY record_date DESC, id DESC"
        
        records = conn.execute(query, params).fetchall()
        
        # Calculate summary with filters
        summary_query_debit = "SELECT COALESCE(SUM(amount), 0) FROM cash_records WHERE type = 'debit'"
        summary_query_kredit = "SELECT COALESCE(SUM(amount), 0) FROM cash_records WHERE type = 'kredit'"
        summary_params = []
        
        if start_date:
            summary_query_debit += " AND date(record_date) >= date(?)"
            summary_query_kredit += " AND date(record_date) >= date(?)"
            summary_params.append(start_date)
        if end_date:
            summary_query_debit += " AND date(record_date) <= date(?)"
            summary_query_kredit += " AND date(record_date) <= date(?)"
            summary_params.append(end_date)
            
        total_debit = conn.execute(summary_query_debit, summary_params).fetchone()[0]
        total_kredit = conn.execute(summary_query_kredit, summary_params).fetchone()[0]
        
        total_kas = total_debit - total_kredit
        
        conn.close()
        
        # Format records for response
        formatted_records = []
        for record in records:
            # Handle date formatting
            date_formatted = ''
            if record['record_date']:
                try:
                    # If it's already a string, parse it
                    if isinstance(record['record_date'], str):
                        from datetime import datetime
                        date_obj = datetime.strptime(record['record_date'].split()[0], '%Y-%m-%d')
                        date_formatted = date_obj.strftime('%d-%m-%Y')
                    else:
                        date_formatted = record['record_date'].strftime('%d-%m-%Y')
                except Exception as e:
                    date_formatted = str(record['record_date'])
                    
            formatted_records.append({
                'id': record['id'],
                'type': record['type'],
                'amount': float(record['amount']),
                'description': record['description'],
                'category': record['category'],
                'record_date_formatted': date_formatted
            })
        
        return jsonify({
            'records': formatted_records,
            'summary': {
                'total_debit': float(total_debit),
                'total_kredit': float(total_kredit),
                'total_kas': float(total_kas)
            }
        })
        
    except Exception as e:
        print(f"Error getting cash records: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-cash-record', methods=['POST'])
@login_required
def add_cash_record():
    try:
        data = request.json
        
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO cash_records (type, amount, description, category, record_date)
               VALUES (?, ?, ?, ?, ?)""",
            (data['type'], data['amount'], data['description'], 
             data.get('category', ''), data['record_date'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Catatan kas berhasil ditambahkan!'})
        
    except Exception as e:
        print(f"Error adding cash record: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-cash-record', methods=['POST'])
@login_required
def update_cash_record():
    try:
        data = request.json
        
        conn = get_db_connection()
        conn.execute(
            """UPDATE cash_records 
               SET type = ?, amount = ?, description = ?, category = ?, record_date = ?
               WHERE id = ?""",
            (data['type'], data['amount'], data['description'], 
             data.get('category', ''), data['record_date'], data['id'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Catatan kas berhasil diupdate!'})
        
    except Exception as e:
        print(f"Error updating cash record: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-cash-record/<int:record_id>', methods=['POST'])
@login_required
def delete_cash_record(record_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM cash_records WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Catatan kas berhasil dihapus!'})
        
    except Exception as e:
        print(f"Error deleting cash record: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-cash-records')
@login_required
def export_cash_records():
    try:
        conn = get_db_connection()
        
        query = """
        SELECT 
            strftime('%d-%m-%Y', record_date) as 'Tanggal',
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
        
        df = pd.read_sql_query(query, conn)
        
        # Calculate summary
        total_debit = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_records WHERE type = 'debit'"
        ).fetchone()[0]
        
        total_kredit = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_records WHERE type = 'kredit'"
        ).fetchone()[0]
        
        conn.close()
        
        # Add summary row
        summary_df = pd.DataFrame([
            {'Tanggal': '', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': ''},
            {'Tanggal': 'RINGKASAN', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': ''},
            {'Tanggal': 'Total Debit', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': float(total_debit)},
            {'Tanggal': 'Total Kredit', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': float(total_kredit)},
            {'Tanggal': 'Saldo Akhir', 'Jenis Transaksi': '', 'Keterangan': '', 'Kategori': '', 'Jumlah': float(total_debit - total_kredit)}
        ])
        
        # Combine data
        final_df = pd.concat([df, summary_df], ignore_index=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Rekap Kas')
            
            # Format the Excel file
            worksheet = writer.sheets['Rekap Kas']
            
            # Set column widths
            worksheet.column_dimensions['A'].width = 15  # Tanggal
            worksheet.column_dimensions['B'].width = 20  # Jenis
            worksheet.column_dimensions['C'].width = 40  # Keterangan
            worksheet.column_dimensions['D'].width = 15  # Kategori
            worksheet.column_dimensions['E'].width = 15  # Jumlah
            
        output.seek(0)
        
        from datetime import datetime
        filename = f'rekap_kas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(output, download_name=filename, as_attachment=True)
        
    except Exception as e:
        print(f"Error exporting cash records: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/debug/check-config')
@login_required
def check_config():
    """Route untuk debugging - cek konfigurasi yang digunakan"""
    return jsonify({
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'database_path': app.config['DATABASE_PATH'],
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'debug': app.config['DEBUG'],
        'testing': app.config['TESTING']
    })

# --- BLOK UNTUK MENJALANKAN SERVER ---
if __name__ == '__main__':
    # Print informasi penting saat server start
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Database path: {app.config['DATABASE_PATH']}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Upload folder exists: {os.path.exists(app.config['UPLOAD_FOLDER'])}")
    app.run(debug=app.config['DEBUG'], port=5001)

