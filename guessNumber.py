import random
import time
import sqlite3  # Add import at the top
import json  # Add this import at the top

class GuessNumberGame:
    def __init__(self):
        self.levels = {"easy": 10, "medium": 7, "hard": 5}  # Difficulty levels and number of attempts
        self.stats = {"games_played": 0, "games_won": 0, "games_lost": 0}  # Game statistics
        self.best_scores = []  # Storing best scores (by number of attempts)
        self.number_to_guess = None  # The number to guess
        self.max_attempts = None  # Maximum number of attempts
        self.range_min = None  # Minimum value of the range
        self.range_max = None  # Maximum value of the range
        self.current_user = None  # Add current user tracking
        
        # Database connection setup
        self.conn = sqlite3.connect('guessNumber.db')
        self.cursor = self.conn.cursor()
        self._initialize_db()

    def _initialize_db(self):
        """Initialize database tables if they don't exist"""
        # Create users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Modified game_stats table to store JSON array
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                difficulty TEXT,
                attempts_array JSON,  
                attempts_count INTEGER,
                won BOOLEAN,
                number_to_guess INTEGER,
                range_min INTEGER,
                range_max INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        self.conn.commit()

    def start_game(self):
        if not self.current_user:
            self.handle_user_auth()
        
        print("Welcome to the 'Guess the Number' game!")
        self.choose_level()  # Choosing the difficulty level
        self.choose_range()  # Specifying the number range
        self.play_game()  # Starting the game process

    def handle_user_auth(self):
        while True:
            print("\n1. Login\n2. Register")
            choice = input("Choose an option (1-2): ").strip()
            
            if choice == "1":
                if self.login():
                    break
            elif choice == "2":
                if self.register():
                    break
            else:
                print("Invalid choice. Please try again.")

    def register(self):
        print("\nRegister new account")
        while True:
            email = input("Enter email: ").strip().lower()
            if not '@' in email:
                print("Invalid email format")
                continue
            
            # Check if email exists
            self.cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if self.cursor.fetchone():
                print("Email already registered")
                return False
            
            password = input("Enter password: ").strip()
            if len(password) < 6:
                print("Password must be at least 6 characters")
                continue
            
            # Insert new user
            self.cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)',
                              (email, password))  # In real app, hash the password!
            self.conn.commit()
            
            # Set current user
            self.cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            self.current_user = self.cursor.fetchone()[0]
            print("Registration successful!")
            return True

    def login(self):
        print("\nLogin")
        email = input("Enter email: ").strip().lower()
        password = input("Enter password: ").strip()
        
        self.cursor.execute('SELECT id, password FROM users WHERE email = ?', (email,))
        result = self.cursor.fetchone()
        
        if result and result[1] == password:  # In real app, verify hash!
            self.current_user = result[0]
            print("Login successful!")
            return True
        else:
            print("Invalid email or password")
            return False

    def choose_level(self):
        print("Choose a difficulty level:")
        for i, level in enumerate(self.levels.keys(), 1):
            print(f"{i}. {level.capitalize()} (attempts: {self.levels[level]})")

        choice = input("Enter the level number: ").strip()
        try:
            level = list(self.levels.keys())[int(choice) - 1]
            self.max_attempts = self.levels[level]
            print(f"You chose the level: {level.capitalize()} (Attempts: {self.max_attempts})")
        except (ValueError, IndexError):
            print("Invalid input. Please enter a number from the list.")
            self.choose_level()


    def choose_range(self):
        print("\nChoose the range for the number to guess.")
        while True:
            min_input = input("Enter the minimum value: ").strip()
            max_input = input("Enter the maximum value: ").strip()

            if min_input.isdigit() and max_input.isdigit():
                self.range_min = int(min_input)
                self.range_max = int(max_input)
                if self.range_min < self.range_max:
                    print(f"Range set: from {self.range_min} to {self.range_max}")
                    break
                else:
                    print("The minimum value must be less than the maximum!")
            else:
                print("Please enter correct numbers.")

    def play_game(self):
        self.number_to_guess = random.randint(self.range_min, self.range_max)  # Generating a random number
        attempts = []  # Array to store all attempts
        print("\nGame started! Guess the number.")
        
        while len(attempts) < self.max_attempts:
            guess_input = input(f"Attempt {len(attempts) + 1}/{self.max_attempts}. Enter a number: ").strip()
            if not guess_input.isdigit():
                print("Please enter a correct number.")
                continue

            guess = int(guess_input)
            attempts.append(guess)  # Store each attempt in the array

            if guess == self.number_to_guess:
                print(f"Congratulations! You guessed the number {self.number_to_guess} in {len(attempts)} attempts!")
                self.stats["games_played"] += 1
                self.stats["games_won"] += 1
                self.best_scores.append(len(attempts))
                self.best_scores = sorted(self.best_scores)[:5]
                
                # Modified database recording to store JSON
                self.cursor.execute('''
                    INSERT INTO game_stats 
                    (user_id, difficulty, attempts_array, attempts_count, won, number_to_guess, range_min, range_max)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (self.current_user,
                      list(self.levels.keys())[list(self.levels.values()).index(self.max_attempts)],
                      json.dumps(attempts),  # Convert list to JSON
                      len(attempts),
                      True, 
                      self.number_to_guess, 
                      self.range_min, 
                      self.range_max))
                self.conn.commit()
                break
            elif guess < self.number_to_guess:
                print("The number is higher!")
            else:
                print("The number is lower!")
        else:
            print(f"You lost! The number was: {self.number_to_guess}")
            self.stats["games_played"] += 1
            self.stats["games_lost"] += 1
            
            # Modified database recording for losses with JSON
            self.cursor.execute('''
                INSERT INTO game_stats 
                (user_id, difficulty, attempts_array, attempts_count, won, number_to_guess, range_min, range_max)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.current_user,
                  list(self.levels.keys())[list(self.levels.values()).index(self.max_attempts)],
                  json.dumps(attempts),  # Convert list to JSON
                  len(attempts),
                  False, 
                  self.number_to_guess, 
                  self.range_min, 
                  self.range_max))
            self.conn.commit()

        self.show_stats()
        self.restart_game()

    def show_stats(self):
        print("\nGame Statistics from Database:")
        
        # Get overall statistics
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as wins,
                AVG(attempts_count) as avg_attempts
            FROM game_stats
            WHERE user_id = ?
        ''', (self.current_user,))
        
        total_games, wins, avg_attempts = self.cursor.fetchone()
        losses = total_games - wins if total_games else 0
        
        print(f"\nOverall Stats:")
        print(f"Total Games: {total_games}")
        print(f"Wins: {wins} ({(wins/total_games)*100:.1f}% win rate)" if total_games else "No games played yet")
        print(f"Losses: {losses}")
        print(f"Average Attempts: {avg_attempts:.1f}" if avg_attempts else "N/A")
        
        # Get statistics by difficulty
        self.cursor.execute('''
            SELECT 
                difficulty,
                COUNT(*) as games,
                SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as wins,
                AVG(attempts_count) as avg_attempts,
                MIN(attempts_count) as best_score
            FROM game_stats
            WHERE user_id = ?
            GROUP BY difficulty
        ''', (self.current_user,))
        
        print("\nStats by Difficulty:")
        for diff, games, diff_wins, diff_avg, best in self.cursor.fetchall():
            print(f"\n{diff.capitalize()}:")
            print(f"  Games: {games}")
            print(f"  Wins: {diff_wins} ({(diff_wins/games)*100:.1f}% win rate)")
            print(f"  Average Attempts: {diff_avg:.1f}")
            print(f"  Best Score: {best} attempts")

    def restart_game(self):
        print("\nDo you want to play again?")
        choice = input("Enter 'yes' or 'no': ").strip().lower()
        if choice == 'yes':
            self.start_game()
        else:
            print("Thanks for playing!")

    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()


if __name__ == "__main__":
    game = GuessNumberGame()
    game.start_game()