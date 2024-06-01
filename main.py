import telebot
import sqlite3
import random
from telebot import types


bot = telebot.TeleBot("7203761071:AAFTxIeMe_6ol7wYgkwiaJoIw8IAcAy_SVA")

conn = sqlite3.connect('words.db')
c = conn.cursor()

# Create tables to store words if not exists
c.execute('''CREATE TABLE IF NOT EXISTS beginner_words
             (id INTEGER PRIMARY KEY, korean TEXT, correct_translation TEXT, incorrect_translation1 TEXT, incorrect_translation2 TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS intermediate_words
             (id INTEGER PRIMARY KEY, korean TEXT, correct_translation TEXT, incorrect_translation1 TEXT, incorrect_translation2 TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS advanced_words
             (id INTEGER PRIMARY KEY, korean TEXT, correct_translation TEXT, incorrect_translation1 TEXT, incorrect_translation2 TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS learned_words
             (user_id INTEGER, word_id INTEGER)''')

conn.commit()

# Function to insert words into the database
def insert_words(level, words):
    if level == 'beginner':
        c.executemany("INSERT INTO beginner_words (korean, correct_translation, incorrect_translation1, incorrect_translation2) VALUES (?, ?, ?, ?)", words)
    elif level == 'intermediate':
        c.executemany("INSERT INTO intermediate_words (korean, correct_translation, incorrect_translation1, incorrect_translation2) VALUES (?, ?, ?, ?)", words)
    elif level == 'advanced':
        c.executemany("INSERT INTO advanced_words (korean, correct_translation, incorrect_translation1, incorrect_translation2) VALUES (?, ?, ?, ?)", words)
    conn.commit()

# Insert sample words into the database
beginner_words = [
    ("안녕하세요", "Hello", "Goodbye", "Thank you"),
    ("사과", "Apple", "Banana", "Orange"),
    ("감사합니다", "Thank you", "Sorry", "Please"),
]
insert_words('beginner', beginner_words)

intermediate_words = [
    ("고양이", "Cat", "Dog", "Bird"),
    ("집", "House", "School", "Park"),
    ("물", "Water", "Fire", "Earth"),
]
insert_words('intermediate', intermediate_words)

advanced_words = [
    ("전화번호", "Phone number", "Address", "Email"),
    ("빨간색", "Red color", "Blue color", "Yellow color"),
    ("비행기", "Airplane", "Train", "Car"),
]
insert_words('advanced', advanced_words)

def get_words_by_level(cursor, level, word_id=None):
    if word_id:
        cursor.execute(f"SELECT * FROM {level}_words WHERE id=?", (word_id,))
        return cursor.fetchone()
    else:
        cursor.execute(f"SELECT * FROM {level}_words")
        return cursor.fetchall()



def select_random_word(words):
    return random.choice(words)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Beginner', 'Intermediate', 'Advanced')
    bot.send_message(message.chat.id, "Choose your level:", reply_markup=markup)
    bot.register_next_step_handler(message, select_mode)


@bot.message_handler(func=lambda message: message.text in ['Beginner', 'Intermediate', 'Advanced'])
def select_mode(message):
    level = message.text.lower()
    if message.text == '🔄Restart':
        start(message)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('With Daily Plan', 'Without Daily Plan')
    markup.add('🔄Restart')
    bot.send_message(message.chat.id, f"Level: {level.capitalize()}\nChoose learning mode:", reply_markup=markup)
    bot.register_next_step_handler(message, start_learning, level)

def start_learning(message, level):
    mode = message.text
    if message.text == '🔄Restart':
        start(message)
        return
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    words = get_words_by_level(c, level)  # Retrieve words based on level
    conn.close()

    if not words:
        bot.send_message(message.chat.id, "No words available for this level.")
        return

    if mode == 'With Daily Plan':
        bot.send_message(message.chat.id, "How many words do you want to learn per day?")
        bot.register_next_step_handler(message, set_daily_limit, level)
    else:
        word = select_random_word(words)
        learn_word(message.chat.id, message, word, level, limit=None, learned_count=0)


# Function to handle setting daily learning limit
def set_daily_limit(message, level):
    if message.text == '🔄Restart':
        start(message)
        return
    try:
        limit = int(message.text)
        conn = sqlite3.connect('words.db')
        c = conn.cursor()
        words = get_words_by_level(c, level)  # Pass the cursor to get_words_by_level
        if limit <= len(words):
            bot.send_message(message.chat.id, f"Your daily learning limit is set to {limit} words.")
            # Store the remaining words in user's context
            learn_next_word(message.chat.id, message, words[:limit], level, limit,  learned_count=0)
        else:
            bot.send_message(message.chat.id, "Daily limit exceeds the number of available words.")
        conn.close()  # Close the connection after using it
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number.")

def learn_next_word(chat_id, message, remaining_words, level, limit, learned_count):
    if message.text == '🔄Restart':
        start(message)
        return
    if remaining_words and (limit is None or learned_count < limit):
        word = select_random_word(remaining_words)
        learn_word(chat_id, message, word, level, limit, learned_count)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Revise Words'))
        markup.add(types.KeyboardButton('🔄Restart'))
        # Add "Revise Words" button
        bot.send_message(chat_id, "You have finished your daily learning session. Click on 'Revise Words' to revise.",
                         reply_markup=markup)

def learn_word(chat_id, message, word, level, limit, learned_count):
    if message.text == '🔄Restart':
        start(message)
        return
    pk, korean, correct_translation, *incorrect_translations = word

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    options = random.sample(incorrect_translations, 2)
    options.append(correct_translation)
    random.shuffle(options)
    markup.add('🔄Restart')
    for option in options:
        markup.add(types.KeyboardButton(option))
    bot.send_message(chat_id, f"What is the English translation of '{korean}'?", reply_markup=markup)

    # Store the Korean word along with the level in the user's context
    bot.register_next_step_handler(message,
                                   lambda msg: check_answer(msg, korean, level, limit, chat_id, pk, learned_count))  # Pass user_id and word_id

@bot.message_handler(func=lambda message: message.text == 'Revise Words')
def handle_revise_words(message):
    if message.text == '🔄Restart':
        start(message)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Beginner', 'Intermediate', 'Advanced')
    markup.add('🔄Restart')
    bot.send_message(message.chat.id, "Choose the level you want to revise:", reply_markup=markup)
    bot.register_next_step_handler(message, revise_words)
@bot.message_handler(func=lambda message: message.text == '🔄Restart')
def handle_restart(message):
    start(message)

def revise_words(message):
    if message.text == '🔄Restart':
        start(message)
        return
    level = message.text.lower()  # or any specific level you want to revise
    user_id = message.from_user.id
    conn = sqlite3.connect('words.db')
    c = conn.cursor()

    # Verify if the level is valid
    if level not in ['beginner', 'intermediate', 'advanced']:
        bot.send_message(message.chat.id, "Invalid level.")
        conn.close()
        return

    # Retrieve learned words for the specific user
    c.execute("SELECT word_id FROM learned_words WHERE user_id=?", (user_id,))
    learned_words = c.fetchall()

    # Retrieve words from the learned words table for the specific user
    words = []
    for word in learned_words:
        word_data = get_words_by_level(c, level, word[0])
        if word_data:
            words.append(word_data)

    conn.close()  # Close the connection after using it

    if words:
        word = select_random_word(words)
        revise_next_word(message.chat.id, message, words, level, learned_count=0)  # Start revising
    else:
        bot.send_message(message.chat.id, "You haven't learned any words yet.")

def revise_next_word(chat_id, message, words, level, learned_count):
    if message.text == '🔄Restart':
        start(message)
        return
    if words and learned_count < len(words):
        word = select_random_word(words)
        learn_word(chat_id, message, word, level, limit=None, learned_count=learned_count)
    else:
        bot.send_message(chat_id, "You have revised all learned words.")
def check_answer(message, korean_word, level, limit, user_id, word_id, learned_count):
    if message.text == '🔄Restart':
        start(message)
        return
    conn = sqlite3.connect('words.db')
    c = conn.cursor()

    try:
        # Retrieve the correct answer from the database based on the question asked
        c.execute(f"SELECT correct_translation FROM {level}_words WHERE korean=?", (korean_word,))
        result = c.fetchone()
        if result is not None:  # Check if result is not None
            correct_translation = result[0]

            # Check if the selected option is correct
            if message.text == correct_translation:
                bot.send_message(message.chat.id, "Correct!")
                # Insert learned word into the learned_words table
                c.execute("INSERT INTO learned_words (user_id, word_id) VALUES (?, ?)", (user_id, word_id))
                conn.commit()
                remaining_words = get_words_by_level(c, level)
                learn_next_word(message.chat.id, message, remaining_words[1:], level, limit, learned_count + 1)  # Pass the remaining words and limit
                # Add logic to track user progress (e.g., update user score, move to the next word)
            else:
                bot.send_message(message.chat.id, f"Wrong! The correct answer is: {correct_translation}")
                remaining_words = get_words_by_level(c, level)
                learn_next_word(message.chat.id, message, remaining_words[1:], level, limit, learned_count + 1)  # Pass the remaining words and limit
                # Add logic to provide feedback and maybe show the correct answer
            # After processing the answer, you might want to ask the next question or provide options to continue
        else:
            bot.send_message(message.chat.id, "No translation found for the given Korean word.")
    finally:
        # Close the connection
        conn.close()


# Start polling
bot.polling()