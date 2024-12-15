import sqlite3
import random
import json
from datetime import datetime, timedelta
from regression import initialize_model, predict_next_guess

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

def simulate_ai_game(model, target, range_min, range_max, player_attempts):
    """Simulate AI guesses for the same game"""
    ai_attempts = []
    last_guess = (range_max + range_min) // 2  # Start with middle
    ai_attempts.append(last_guess)
    
    for attempt_count in range(1, len(player_attempts)):
        if last_guess == target:
            break
            
        # Determine feedback for the last guess
        if last_guess > target:
            feedback = -1
        elif last_guess < target:
            feedback = 1
        else:
            feedback = 0
            
        # Get AI's next guess
        next_guess = predict_next_guess(
            model,
            range_min,
            range_max,
            last_guess,
            attempt_count,
            feedback
        )
        
        ai_attempts.append(next_guess)
        last_guess = next_guess
        
        if last_guess == target:
            break
            
    return ai_attempts

def simulate_games():
    # Initialize the AI model
    print("Initializing AI model...")
    try:
        model = initialize_model()
    except Exception as e:
        print(f"Failed to initialize AI model: {e}")
        model = None  # Set model to None if initialization fails
    
    # Connect to database
    conn = sqlite3.connect('guessNumber.db')
    cursor = conn.cursor()
    
    # Add AI player if not exists
    cursor.execute('INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)', 
                  ('ai.player@game.com', 'test'))
    cursor.execute('SELECT id FROM users WHERE email = ?', ('ai.player@game.com',))
    ai_user_id = cursor.fetchone()[0]
    
    # Difficulty levels configuration
    levels = {"easy": 10, "medium": 7, "hard": 5}
    
    # Generate 5 players
    players = [
        ("player1@test.com", "test"),
        ("player2@test.com", "test"),
        ("player3@test.com", "test"),
        ("player4@test.com", "test"),
        ("player5@test.com", "test"),
        ("player6@test.com", "test"),
        ("player7@test.com", "test"),
        ("player8@test.com", "test"),
        ("player9@test.com", "test"),
        ("player10@test.com", "test")
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
            
            # Generate AI attempts for the same game only if model is available
            if model:
                ai_attempts = simulate_ai_game(
                    model, number_to_guess, range_min, range_max, attempts
                )
                ai_won = ai_attempts[-1] == number_to_guess
            else:
                ai_attempts = []
                ai_won = False
            
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
            
            # Insert AI game data only if AI model was available
            if model:
                cursor.execute(''' 
                    INSERT INTO game_stats 
                    (user_id, timestamp, difficulty, attempts_array, attempts_count, 
                     won, number_to_guess, range_min, range_max)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ai_user_id,
                    game_time.strftime('%Y-%m-%d %H:%M:%S'),
                    difficulty,
                    json.dumps(ai_attempts),
                    len(ai_attempts),
                    ai_won,
                    number_to_guess,
                    range_min,
                    range_max
                ))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    simulate_games()
    print("Simulation completed successfully!")
