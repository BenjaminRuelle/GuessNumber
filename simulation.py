import sqlite3
import random
import json
from datetime import datetime, timedelta

def generate_realistic_attempts(target, min_val, max_val, max_attempts):
    """Generate realistic sequence of guesses based on binary search with some randomness"""
    attempts = []
    low = min_val
    high = max_val
    
    while len(attempts) < max_attempts:
        # Add some randomness to make it more realistic
        if random.random() < 0.2:  # 20% chance of making a "random" guess
            guess = random.randint(low, high)
        else:
            # Use binary search with some randomness
            guess = (low + high) // 2 + random.randint(-2, 2)
            guess = max(min_val, min(max_val, guess))  # Keep within bounds
        
        attempts.append(guess)
        
        if guess == target:
            break
        elif guess < target:
            low = guess + 1
        else:
            high = guess - 1
            
    return attempts

def simulate_games():
    # Connect to database
    conn = sqlite3.connect('guessNumber.db')
    cursor = conn.cursor()
    
    # Difficulty levels configuration
    levels = {"easy": 10, "medium": 7, "hard": 5}
    
    # Generate 5 players
    players = [
        ("player1@test.com", "password123"),
        ("player2@test.com", "password456"),
        ("player3@test.com", "password789"),
        ("player4@test.com", "passwordabc"),
        ("player5@test.com", "passworddef")
    ]
    
    # Register players
    for email, password in players:
        cursor.execute('INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)', 
                      (email, password))
    conn.commit()
    
    # Simulate games for each player
    base_time = datetime.now() - timedelta(days=30)  # Start from 30 days ago
    
    for email, _ in players:
        # Get user_id
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        user_id = cursor.fetchone()[0]
        
        # Random number of games (5-10) for this player
        num_games = random.randint(5, 10)
        
        for game_num in range(num_games):
            # Random difficulty
            difficulty = random.choice(list(levels.keys()))
            max_attempts = levels[difficulty]
            
            # Random range (keeping it reasonable)
            range_min = random.randint(1, 50)
            range_max = range_min + random.randint(20, 100)
            
            # Generate target number
            number_to_guess = random.randint(range_min, range_max)
            
            # Generate realistic attempts
            attempts = generate_realistic_attempts(
                number_to_guess, range_min, range_max, max_attempts
            )
            
            # Determine if game was won
            won = attempts[-1] == number_to_guess
            
            # Calculate timestamp for this game
            game_time = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # Insert game data
            cursor.execute('''
                INSERT INTO game_stats 
                (user_id, timestamp, difficulty, attempts_array, attempts_count, 
                 won, number_to_guess, range_min, range_max)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                game_time.strftime('%Y-%m-%d %H:%M:%S'),
                difficulty,
                json.dumps(attempts),
                len(attempts),
                won,
                number_to_guess,
                range_min,
                range_max
            ))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    simulate_games()
    print("Simulation completed successfully!")
