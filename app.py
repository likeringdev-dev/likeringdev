import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime
import hashlib
import uuid

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave-temporal-cambiar')

# Función para conectar a la base de datos
def get_db_connection():
    try:
        conn = psycopg2.connect(
            os.getenv('DATABASE_URL'),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

# Función para hashear contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==================== RUTAS HTML ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perfil')
def perfil():
    return render_template('perfil.html')

@app.route('/videos')
def videos():
    return render_template('videos.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/mensajes')
def mensajes():
    return render_template('mensajes.html')

@app.route('/streamer')
def streamer():
    return render_template('streamer.html')

@app.route('/billetera')
def billetera():
    return render_template('billetera.html')

@app.route('/editor')
def editor():
    return render_template('editor.html')

# ==================== API ENDPOINTS ====================

# API: Registro de usuario
# API: Registro de nuevos usuarios
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        # Asumiendo que el campo de la URL de la imagen se llama 'imageUrl' en el frontend
        imageUrl = data.get('imageUrl') 
        
        if not all([username, password, imageUrl]):
            return jsonify({'success': False, 'message': 'Faltan datos de registro (usuario, contraseña o imagen)'}), 400

        hashed_password = hash_password(password)

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'}), 500
        
        cur = conn.cursor()
        
        # 1. Verificar si el usuario ya existe
        cur.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'El nombre de usuario ya existe'}), 409

        # 2. Insertar nuevo usuario en la tabla 'usuarios'
        # Usamos gen_random_uuid() para el ID y 'azul' como plan por defecto, basado en tus snippets y la imagen
        cur.execute('''
            INSERT INTO usuarios (id, username, password, plan, image_url)
            VALUES (gen_random_uuid(), %s, %s, %s, %s)
            RETURNING id;
        ''', (username, hashed_password, 'azul', imageUrl))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Respuesta exitosa que el frontend espera
        return jsonify({'success': True, 'message': 'Registro exitoso'})
        
    except Exception as e:
        print(f"Error en la ruta /api/register: {e}")
        return jsonify({'success': False, 'message': f'Error interno del servidor: {str(e)}'}), 500

# API: Login de usuario
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Usuario y contraseña requeridos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        password_hash = hash_password(password)
        
        cur.execute('''
            SELECT username, image_url, plan, likes, followers, following,
                   likes_disponibles, likes_ganados, dinero_ganado
            FROM usuarios
            WHERE username = %s AND password = %s
        ''', (username, password_hash))
        
        user = cur.fetchone()
        
        if user:
            # Actualizar última conexión
            cur.execute('UPDATE usuarios SET ultima_conexion = NOW() WHERE username = %s', (username,))
            conn.commit()
            
            user_data = dict(user)
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'data': user_data
            })
        else:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'}), 401
            
    except Exception as e:
        print(f"Error en login: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Obtener perfil de usuario
@app.route('/api/user-profile', methods=['GET'])
def get_user_profile():
    try:
        username = request.args.get('user')
        if not username:
            return jsonify({'success': False, 'message': 'Usuario requerido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT username, image_url, plan, likes, followers, following
            FROM usuarios
            WHERE username = %s
        ''', (username,))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user:
            return jsonify({
                'success': True,
                'data': dict(user)
            })
        else:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
            
    except Exception as e:
        print(f"Error obteniendo perfil: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Obtener videos de un usuario
@app.route('/api/user-videos', methods=['GET'])
def get_user_videos():
    try:
        username = request.args.get('user')
        if not username:
            return jsonify({'success': False, 'message': 'Usuario requerido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT video_id, titulo, descripcion, video_url, thumbnail_url,
                   music_name, likes, visualizaciones, comentarios, fecha_subida
            FROM videos
            WHERE username = %s
            ORDER BY fecha_subida DESC
        ''', (username,))
        
        videos = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': [dict(v) for v in videos]
        })
        
    except Exception as e:
        print(f"Error obteniendo videos: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Obtener todos los videos (para feed)
@app.route('/api/all-videos', methods=['GET'])
def get_all_videos():
    try:
        current_user = request.args.get('user')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT v.video_id, v.username as user, v.titulo, v.descripcion as description,
                   v.video_url, v.thumbnail_url, v.music_name as music,
                   v.likes, v.visualizaciones, v.comentarios as comments,
                   u.image_url as profile_img,
                   CASE WHEN l.username IS NOT NULL THEN true ELSE false END as is_liked,
                   CASE WHEN s.follower IS NOT NULL THEN true ELSE false END as is_following
            FROM videos v
            JOIN usuarios u ON v.username = u.username
            LEFT JOIN likes l ON v.video_id = l.video_id AND l.username = %s
            LEFT JOIN seguidores s ON v.username = s.following AND s.follower = %s
            ORDER BY v.fecha_subida DESC
        ''', (current_user, current_user))
        
        videos = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': [dict(v) for v in videos]
        })
        
    except Exception as e:
        print(f"Error obteniendo videos: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Guardar video
@app.route('/api/save-video', methods=['POST'])
def save_video():
    try:
        data = request.get_json()
        username = data.get('usuario')
        titulo = data.get('titulo')
        descripcion = data.get('descripcion')
        video_url = data.get('videoUrl')
        thumbnail_url = data.get('thumbnailUrl')
        music_url = data.get('musicUrl', '')
        
        if not all([username, titulo, video_url, thumbnail_url]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        # Generar ID único para el video
        video_id = str(uuid.uuid4())
        
        cur.execute('''
            INSERT INTO videos (video_id, username, titulo, descripcion, video_url,
                              thumbnail_url, music_url, music_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (video_id, username, titulo, descripcion, video_url,
              thumbnail_url, music_url, music_url))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Video guardado exitosamente',
            'videoId': video_id
        })
        
    except Exception as e:
        print(f"Error guardando video: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Dar like a un video
@app.route('/api/like-video', methods=['POST'])
def like_video():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        username = data.get('username')
        
        if not all([video_id, username]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        # Verificar si ya dio like
        cur.execute('SELECT id FROM likes WHERE video_id = %s AND username = %s',
                   (video_id, username))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ya diste like a este video'}), 400
        
        # Registrar like
        cur.execute('INSERT INTO likes (video_id, username) VALUES (%s, %s)',
                   (video_id, username))
        
        # Actualizar contador
        cur.execute('UPDATE videos SET likes = likes + 1 WHERE video_id = %s', (video_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Like registrado'})
        
    except Exception as e:
        print(f"Error dando like: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Registrar visualización
@app.route('/api/record-view', methods=['POST'])
def record_view():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        username = data.get('username')
        
        if not all([video_id, username]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        # Registrar vista
        cur.execute('INSERT INTO vistas (video_id, username) VALUES (%s, %s)',
                   (video_id, username))
        
        # Actualizar contador
        cur.execute('''
            UPDATE videos SET visualizaciones = visualizaciones + 1
            WHERE video_id = %s
            RETURNING visualizaciones
        ''', (video_id,))
        
        result = cur.fetchone()
        new_view_count = result['visualizaciones'] if result else 0
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'newViewCount': new_view_count
        })
        
    except Exception as e:
        print(f"Error registrando vista: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Obtener comentarios
@app.route('/api/comments', methods=['GET'])
def get_comments():
    try:
        video_id = request.args.get('videoId')
        if not video_id:
            return jsonify({'success': False, 'message': 'Video ID requerido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT c.comment_id, c.username, c.comment_text as "commentText",
                   c.timestamp, c.edited, u.image_url
            FROM comentarios c
            JOIN usuarios u ON c.username = u.username
            WHERE c.video_id = %s
            ORDER BY c.timestamp DESC
        ''', (video_id,))
        
        comments = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': [dict(c) for c in comments]
        })
        
    except Exception as e:
        print(f"Error obteniendo comentarios: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Agregar comentario
@app.route('/api/add-comment', methods=['POST'])
def add_comment():
    try:
        data = request.get_json()
        video_id = data.get('videoId')
        username = data.get('username')
        comment_text = data.get('commentText')
        
        if not all([video_id, username, comment_text]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        # Obtener imagen del usuario
        cur.execute('SELECT image_url FROM usuarios WHERE username = %s', (username,))
        user = cur.fetchone()
        image_url = user['image_url'] if user else ''
        
        # Generar ID único para el comentario
        comment_id = str(uuid.uuid4())
        
        # Insertar comentario
        cur.execute('''
            INSERT INTO comentarios (comment_id, video_id, username, comment_text, image_url)
            VALUES (%s, %s, %s, %s, %s)
        ''', (comment_id, video_id, username, comment_text, image_url))
        
        # Actualizar contador
        cur.execute('UPDATE videos SET comentarios = comentarios + 1 WHERE video_id = %s',
                   (video_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Comentario agregado',
            'commentId': comment_id
        })
        
    except Exception as e:
        print(f"Error agregando comentario: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Seguir usuario
@app.route('/api/follow-user', methods=['POST'])
def follow_user():
    try:
        data = request.get_json()
        follower = data.get('follower')
        following = data.get('following')
        
        if not all([follower, following]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        if follower == following:
            return jsonify({'success': False, 'message': 'No puedes seguirte a ti mismo'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        # Verificar si ya sigue
        cur.execute('SELECT id FROM seguidores WHERE follower = %s AND following = %s',
                   (follower, following))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Ya sigues a este usuario'}), 400
        
        # Registrar seguimiento
        cur.execute('INSERT INTO seguidores (follower, following) VALUES (%s, %s)',
                   (follower, following))
        
        # Actualizar contadores
        cur.execute('UPDATE usuarios SET following = following + 1 WHERE username = %s',
                   (follower,))
        cur.execute('UPDATE usuarios SET followers = followers + 1 WHERE username = %s',
                   (following,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Ahora sigues a @{following}'
        })
        
    except Exception as e:
        print(f"Error siguiendo usuario: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Obtener conversaciones
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    try:
        username = request.args.get('user')
        if not username:
            return jsonify({'success': False, 'message': 'Usuario requerido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            WITH latest_messages AS (
                SELECT DISTINCT ON (
                    CASE
                        WHEN remitente = %s THEN destinatario
                        ELSE remitente
                    END
                )
                CASE
                    WHEN remitente = %s THEN destinatario
                    ELSE remitente
                END as username,
                mensaje, timestamp, remitente,
                (SELECT COUNT(*) FROM mensajes m2
                 WHERE m2.destinatario = %s
                 AND m2.remitente = CASE
                    WHEN m.remitente = %s THEN m.destinatario
                    ELSE m.remitente
                 END
                 AND m2.leido = false) as unread_count
                FROM mensajes m
                WHERE remitente = %s OR destinatario = %s
                ORDER BY
                    CASE
                        WHEN remitente = %s THEN destinatario
                        ELSE remitente
                    END,
                    timestamp DESC
            )
            SELECT lm.username, lm.mensaje as last_message_text,
                   lm.timestamp as last_message_timestamp, lm.remitente as last_message_from,
                   lm.unread_count, u.image_url
            FROM latest_messages lm
            JOIN usuarios u ON lm.username = u.username
            ORDER BY lm.timestamp DESC
        ''', (username, username, username, username, username, username, username))
        
        conversations = cur.fetchall()
        cur.close()
        conn.close()
        
        result = []
        for conv in conversations:
            result.append({
                'username': conv['username'],
                'imageUrl': conv['image_url'],
                'lastMessage': {
                    'text': conv['last_message_text'],
                    'timestamp': conv['last_message_timestamp'].isoformat(),
                    'from': conv['last_message_from']
                },
                'unreadCount': conv['unread_count']
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"Error obteniendo conversaciones: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Obtener mensajes entre dos usuarios
@app.route('/api/messages', methods=['GET'])
def get_messages():
    try:
        user1 = request.args.get('user1')
        user2 = request.args.get('user2')
        
        if not all([user1, user2]):
            return jsonify({'success': False, 'message': 'Usuarios requeridos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            SELECT message_id, remitente as "from", destinatario as "to",
                   mensaje as message, leido as read, timestamp, read_at
            FROM mensajes
            WHERE (remitente = %s AND destinatario = %s)
               OR (remitente = %s AND destinatario = %s)
            ORDER BY timestamp ASC
        ''', (user1, user2, user2, user1))
        
        messages = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': [dict(m) for m in messages]
        })
        
    except Exception as e:
        print(f"Error obteniendo mensajes: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Enviar mensaje
@app.route('/api/send-message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        remitente = data.get('from')
        destinatario = data.get('to')
        mensaje = data.get('message')
        
        if not all([remitente, destinatario, mensaje]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        
        message_id = str(uuid.uuid4())
        
        cur.execute('''
            INSERT INTO mensajes (message_id, remitente, destinatario, mensaje)
            VALUES (%s, %s, %s, %s)
        ''', (message_id, remitente, destinatario, mensaje))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Mensaje enviado',
            'messageId': message_id
        })
        
    except Exception as e:
        print(f"Error enviando mensaje: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API: Marcar mensajes como leídos
@app.route('/api/mark-as-read', methods=['POST'])
def mark_as_read():
    try:
        data = request.get_json()
        remitente = data.get('from')
        destinatario = data.get('to')
        
        if not all([remitente, destinatario]):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        cur = conn.cursor()
        cur.execute('''
            UPDATE mensajes
            SET leido = true, read_at = NOW()
            WHERE remitente = %s AND destinatario = %s AND leido = false
        ''', (remitente, destinatario))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error marcando como leído: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)