import sqlite3
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
import os
import io

# Inisialisasi Aplikasi Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Fungsi untuk koneksi ke database
def get_db_connection():
    conn = sqlite3.connect('instance/store.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Rute untuk Halaman Utama ---
@app.route('/')
def admin_dashboard():
    return render_template('admin.html')

# --- API UNTUK MANAJEMEN KITAB ---

@app.route('/api/add-book', methods=['POST'])
def add_book():
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO books (name, price, availability, link_ig, link_wa, link_shopee, link_tiktok)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data['name'], data['price'], data['availability'], data.get('link_ig'), data.get('link_wa'), data.get('link_shopee'), data.get('link_tiktok'))
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Kitab baru berhasil ditambahkan!'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nama kitab sudah ada.'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/books/all', methods=['GET'])
def get_all_books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(row) for row in books])

@app.route('/api/books', methods=['GET'])
def get_available_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books WHERE availability = 'Tersedia' ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(row) for row in books])

@app.route('/api/book/<int:book_id>', methods=['GET'])
def get_book_details(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    if book is None:
        return jsonify({'error': 'Kitab tidak ditemukan'}), 404
    return jsonify(dict(book))

@app.route('/api/update-book', methods=['POST'])
def update_book():
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute(
            """UPDATE books 
               SET name = ?, price = ?, availability = ?, link_ig = ?, link_wa = ?, link_shopee = ?, link_tiktok = ?
               WHERE id = ?""",
            (data['name'], data['price'], data['availability'], data.get('link_ig'), data.get('link_wa'), data.get('link_shopee'), data.get('link_tiktok'), data['id'])
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Data kitab berhasil diupdate!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- API UNTUK PEMBELI & IMPORT ---

@app.route('/api/offline-buyers', methods=['GET'])
def get_offline_buyers():
    conn = get_db_connection()
    buyers = conn.execute('SELECT * FROM offline_buyers ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(row) for row in buyers])

@app.route('/api/import-buyers', methods=['POST'])
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

# --- API UNTUK REKAP PENJUALAN ---

@app.route('/api/add-offline-sale', methods=['POST'])
def add_offline_sale():
    data = request.json
    try:
        conn = get_db_connection()
        book = conn.execute('SELECT price FROM books WHERE id = ?', (data['book_id'],)).fetchone()
        if not book:
            return jsonify({'error': 'Kitab tidak ditemukan'}), 404
        
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
def add_online_sale():
    data = request.json
    try:
        conn = get_db_connection()
        book = conn.execute('SELECT price FROM books WHERE id = ?', (data['book_id'],)).fetchone()
        if not book:
            return jsonify({'error': 'Kitab tidak ditemukan'}), 404
        
        shipping_cost = 15000
        total_price = book['price'] + shipping_cost

        conn.execute(
            # Tambahkan transfer_date di sini
            'INSERT INTO online_sales (buyer_name, buyer_address, book_id, shipping_cost, total_price, transfer_date) VALUES (?, ?, ?, ?, ?, ?)',
            (data['buyer_name'], data['buyer_address'], data['book_id'], shipping_cost, total_price, data['transfer_date'])
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Rekap online berhasil ditambahkan!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# GANTI FUNGSI INI: untuk menampilkan tanggal transfer di riwayat
@app.route('/api/recent-online-sales')
def get_all_online_sales(): # Nama fungsi tetap sama agar tidak merusak JS
    conn = get_db_connection()
    query = """
    SELECT 
        os.id, 
        os.buyer_name, 
        os.buyer_address, 
        b.name as book_name, 
        os.shipping_cost, 
        os.total_price,
        strftime('%d-%m-%Y %H:%M', os.sale_date) as sale_date_formatted,
        strftime('%d-%m-%Y', os.transfer_date) as transfer_date_formatted -- Tambahkan ini
    FROM online_sales os
    JOIN books b ON os.book_id = b.id
    ORDER BY os.id DESC
    """
    sales = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in sales])


@app.route('/api/recent-offline-sales')
def get_all_offline_sales(): # Ganti nama fungsi agar lebih sesuai
    conn = get_db_connection()
    query = """
    SELECT 
        os.id, 
        ob.name as buyer_name, 
        ob.address, 
        ob.dormitory, 
        b.name as book_name, 
        os.quantity, 
        os.total_price,
        strftime('%d-%m-%Y %H:%M', os.sale_date) as sale_date_formatted
    FROM offline_sales os
    JOIN offline_buyers ob ON os.buyer_id = ob.id
    JOIN books b ON os.book_id = b.id
    ORDER BY os.id DESC
    """
    sales = conn.execute(query).fetchall()
    conn.close()
    return jsonify([dict(row) for row in sales])

# --- API UNTUK EXPORT EXCEL ---

# GANTI FUNGSI EXPORT OFFLINE
@app.route('/api/export-offline-sales')
def export_offline():
    conn = get_db_connection()
    query = """
    SELECT 
        strftime('%d-%m-%Y %H:%M', os.sale_date) as 'Tanggal Transaksi', 
        ob.name as 'Nama Pembeli', 
        ob.address as 'Alamat',
        ob.dormitory as 'Asrama',
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
    
    return send_file(output, download_name='semua_rekap_offline.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/export-online-sales')
def export_online():
    conn = get_db_connection()
    query = """
    SELECT 
        strftime('%d-%m-%Y %H:%M', os.sale_date) as 'Tanggal Transaksi', 
        strftime('%d-%m-%Y', os.transfer_date) as 'Tanggal Transfer', -- Tambahkan ini
        os.buyer_name as 'Nama Pembeli', 
        os.buyer_address as 'Alamat Pengiriman', 
        b.name as 'Nama Kitab', 
        b.price as 'Harga Kitab', 
        os.shipping_cost as 'Ongkir', 
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
    
    return send_file(output, download_name='semua_rekap_online.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# --- BLOK UNTUK MENJALANKAN SERVER (HARUS SELALU DI PALING BAWAH) ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
