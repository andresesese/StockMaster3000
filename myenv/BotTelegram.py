import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext

# Configura il logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Funzione per gestire il comando /start
async def start(update: Update, context: CallbackContext):
    message = "Ciao! Benvenuto nel bot. Per effettuare il login, scrivi /login seguito dal tuo nome utente e dalla password, ad esempio: /login nomeutente password. Per registrarti, scrivi /register seguito dal nome utente desiderato e dalla password, ad esempio: /register nomeutente password."
    await update.message.reply_text(message)

# Funzione per gestire il comando /login
async def login(update: Update, context: CallbackContext):
    global current_username, is_logged
    data = update.message.text.split(maxsplit=1)[1].split()
    username = data[0]
    password = data[1]
    
    # Verifica se l'username è presente nel database
    if not check_username_exists(username):
        message = "Login fallito. Nome utente non trovato."
    else:
        # Verifica se la password corrisponde all'username nel database
        if verify_user_credentials(username, password):
            current_username = username
            is_logged = True
            message = "Login avvenuto con successo! Scrivi /help per la lista dei comandi."
        else:
            message = "Login fallito. Password errata."
    await update.message.reply_text(message)

# Funzione per gestire il comando /register
async def register(update: Update, context: CallbackContext):
    global current_username, is_logged
    data = update.message.text.split(maxsplit=1)[1].split()
    username = data[0]
    password = data[1]
    
    # Verifica se l'username è già presente nel database
    if check_username_exists(username):
        message = "Registrazione fallita. Nome utente già in uso."
    else:
        # Salva il nome utente e la password nel database
        save_user_credentials(username, password)
        current_username = username
        is_logged = True
        message = "Registrazione e login avvenuti con successo! Scrivi /help per la lista dei comandi."
    await update.message.reply_text(message)

# Funzione per gestire il comando /logout
async def logout(update: Update, context: CallbackContext):
    global is_logged, current_username
    is_logged = False
    current_username = ""
    message = "Logout avvenuto con successo. Per effettuare nuovamente il login, scrivi /login seguito dal tuo nome utente e dalla password."
    await update.message.reply_text(message)

# Funzione per gestire il comando /help
async def help_command(update: Update, context: CallbackContext):
    message = "Ecco la lista dei comandi disponibili:\n" \
              "/show: Mostra tutti gli oggetti nel magazzino.\n" \
              "/add <nome> <descrizione>: Aggiunge un nuovo oggetto al magazzino.\n" \
              "/addc <nome_oggetto> <nome_campo> <descrizione_campo>: Aggiunge un nuovo campo a un oggetto esistente.\n" \
              "/delete <nome_oggetto>: Elimina un oggetto dal magazzino.\n" \
              "/logout: Esegue il logout dall'account attuale."
    await update.message.reply_text(message)


# Funzione per mostrare tutti gli oggetti nel magazzino
async def show(update: Update, context: CallbackContext):
    global current_username
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM oggetti WHERE nomeUtente=?", (current_username,))
    result = cursor.fetchall()
    conn.close()

    if result:
        message = "Ecco i tuoi oggetti nel magazzino:\n"
        for row in result:
            message += f"Nome oggetto: {row[1]}\nDescrizione oggetto: {row[2]}\nCampi aggiuntivi:\n"
            message += get_additional_fields(row[0])
            message += "\n"
    else:
        message = "Non hai ancora oggetti nel magazzino."
    
    await update.message.reply_text(message)

# Funzione per gestire il comando /add
async def add(update: Update, context: CallbackContext):
    global current_username
    data = update.message.text.split(maxsplit=1)[1].split(maxsplit=2)
    nome = data[0]
    descrizione = " ".join(data[1:])
    
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO oggetti (nome, descrizione, nomeUtente) VALUES (?, ?, ?)", (nome, descrizione, current_username))
    conn.commit()
    conn.close()

    message = f"Oggetto '{nome}' aggiunto con successo al tuo magazzino."
    await update.message.reply_text(message)


# Funzione per aggiungere un campo a un oggetto esistente
async def addc(update: Update, context: CallbackContext):
    global current_username
    data = update.message.text.split(maxsplit=1)[1].split(maxsplit=2)
    nome_oggetto = data[0]
    nome_campo = data[1]
    descrizione_campo = data[2]
    
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM oggetti WHERE nome=? AND nomeUtente=?", (nome_oggetto, current_username))
    result = cursor.fetchone()
    if result:
        oggetto_id = result[0]
        cursor.execute("INSERT INTO campi (nome, descrizione, nomeOggetto) VALUES (?, ?, ?)", (nome_campo, descrizione_campo, oggetto_id))
        conn.commit()
        message = f"Campo '{nome_campo}' aggiunto con successo all'oggetto '{nome_oggetto}'."
    else:
        message = f"Errore: l'oggetto '{nome_oggetto}' non esiste o non ti appartiene."
    conn.close()

    await update.message.reply_text(message)

# Funzione per eliminare un oggetto dal magazzino
async def delete(update: Update, context: CallbackContext):
    global current_username
    nome_oggetto = update.message.text.split(maxsplit=1)[1]
    
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM oggetti WHERE nome=? AND nomeUtente=?", (nome_oggetto, current_username))
    result = cursor.fetchone()
    if result:
        oggetto_id = result[0]
        cursor.execute("DELETE FROM campi WHERE nomeOggetto=?", (oggetto_id,))
        cursor.execute("DELETE FROM oggetti WHERE id=?", (oggetto_id,))
        conn.commit()
        message = f"Oggetto '{nome_oggetto}' eliminato con successo dal tuo magazzino."
    else:
        message = f"Errore: l'oggetto '{nome_oggetto}' non esiste o non ti appartiene."
    conn.close()

    await update.message.reply_text(message)

# Funzione per ottenere i campi aggiuntivi di un oggetto
def get_additional_fields(oggetto_id):
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nome, descrizione FROM campi WHERE nomeOggetto=?", (oggetto_id,))
    result = cursor.fetchall()
    conn.close()

    additional_fields = ""
    for row in result:
        additional_fields += f"{row[0]}: {row[1]}\n"
    return additional_fields

# Funzione per controllare se un nome utente è già nel database
def check_username_exists(username):
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utenti WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Funzione per verificare le credenziali dell'utente nel database
def verify_user_credentials(username, password):
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utenti WHERE username=? AND password=?", (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Funzione per salvare le credenziali dell'utente nel database
def save_user_credentials(username, password):
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO utenti (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

def main():
    # Creazione del database SQLite e delle tabelle
    conn = sqlite3.connect('stockMaster.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS utenti (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS oggetti (id INTEGER PRIMARY KEY, nome TEXT, descrizione TEXT, nomeUtente TEXT, FOREIGN KEY (nomeUtente) REFERENCES utenti(username))")
    cursor.execute("CREATE TABLE IF NOT EXISTS campi (id INTEGER PRIMARY KEY, nome TEXT, descrizione TEXT, nomeOggetto INTEGER, FOREIGN KEY (nomeOggetto) REFERENCES oggetti(id))")
    conn.close()

    application = ApplicationBuilder().token('TOKEN').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('login', login))
    application.add_handler(CommandHandler('register', register))
    application.add_handler(CommandHandler('logout', logout))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('show', show))
    application.add_handler(CommandHandler('add', add))
    application.add_handler(CommandHandler('addc', addc))
    application.add_handler(CommandHandler('delete', delete))

    application.run_polling()

if __name__ == '__main__':
    main()
