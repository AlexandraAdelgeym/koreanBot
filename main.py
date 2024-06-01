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

# Function to retrieve words based on level
def get_words_by_level(cursor, level):
    cursor.execute(f"SELECT * FROM {level}_words")
    return cursor.fetchall()

# Function to select a random word
def select_random_word(words):
    return random.choice(words)

# Function to handle level selection
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Beginner', 'Intermediate', 'Advanced')
    bot.send_message(message.chat.id, "Choose your level:", reply_markup=markup)
    bot.register_next_step_handler(message, select_mode)

# Function to handle learning mode selection
@bot.message_handler(func=lambda message: message.text in ['Beginner', 'Intermediate', 'Advanced'])
def select_mode(message):
    level = message.text.lower()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('With Daily Plan', 'Without Daily Plan')
    bot.send_message(message.chat.id, f"Level: {level.capitalize()}\nChoose learning mode:", reply_markup=markup)
    bot.register_next_step_handler(message, start_learning, level)

# Function to handle learning words
def start_learning(message, level):
    mode = message.text
    if mode == 'With Daily Plan':
        bot.send_message(message.chat.id, "How many words do you want to learn per day?")
        bot.register_next_step_handler(message, set_daily_limit, level)
    else:
        words = get_words_by_level(c, level)  # Pass the cursor to get_words_by_level
        word = select_random_word(words)
        learn_word(message.chat.id, message, word, level)  # Pass the message as well

# Function to handle setting daily learning limit
def set_daily_limit(message, level):
    try:
        limit = int(message.text)
        conn = sqlite3.connect('words.db')
        c = conn.cursor()
        words = get_words_by_level(c, level)  # Pass the cursor to get_words_by_level
        if limit <= len(words):
            bot.send_message(message.chat.id, f"Your daily learning limit is set to {limit} words.")
            # Store the remaining words in user's context
            learn_next_word(message.chat.id, message, words[:limit], level, limit)
        else:
            bot.send_message(message.chat.id, "Daily limit exceeds the number of available words.")
        conn.close()  # Close the connection after using it
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid number.")

def learn_next_word(chat_id, message, remaining_words, level, limit):
    if remaining_words:
        word = select_random_word(remaining_words)
        learn_word(chat_id, message, word, level, limit)
    else:
        bot.send_message(chat_id, "You have finished your daily learning session.")


def learn_word(chat_id, message, word, level, limit):
    pk, korean, correct_translation, *incorrect_translations = word

    # Check if the current word exceeds the daily limit
    if limit <= 0:
        bot.send_message(chat_id, "You have reached your daily limit of words.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    options = random.sample(incorrect_translations, 2)
    options.append(correct_translation)
    random.shuffle(options)
    for option in options:
        markup.add(types.KeyboardButton(option))
    bot.send_message(chat_id, f"What is the English translation of '{korean}'?", reply_markup=markup)

    # Store the Korean word along with the level in the user's context
    bot.register_next_step_handler(message,
                                   lambda msg: check_answer(msg, korean, level, limit - 1))  # Decrement limit by 1


@bot.message_handler(commands=['revise'])
def revise_words(message):
    level = message.text.lower()  # or any specific level you want to revise
    words = get_words_by_level(level)
    if words:
        word = select_random_word(words)
        learn_word(message.chat.id, message, word, level)
    else:
        bot.send_message(message.chat.id, "No words available for revision.")

# Function to handle answer selection
def check_answer(message, korean_word, level, limit):
    # Create a new SQLite connection and cursor
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
                remaining_words = get_words_by_level(c, level)
                learn_next_word(message.chat.id, message, remaining_words[1:], level, limit)  # Pass the remaining words and limit
                # Add logic to track user progress (e.g., update user score, move to the next word)
            else:
                bot.send_message(message.chat.id, f"Wrong! The correct answer is: {correct_translation}")
                remaining_words = get_words_by_level(c, level)
                learn_next_word(message.chat.id, message, remaining_words[1:], level, limit)  # Pass the remaining words and limit
                # Add logic to provide feedback and maybe show the correct answer
            # After processing the answer, you might want to ask the next question or provide options to continue
        else:
            bot.send_message(message.chat.id, "No translation found for the given Korean word.")
    finally:
        # Close the connection
        conn.close()


# Start polling
bot.polling()