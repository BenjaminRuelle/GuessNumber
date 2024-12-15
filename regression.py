import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import json

def load_and_process_data():
    # Connect to the database
    conn = sqlite3.connect('guessNumber.db')
    
    # Query to get the game data
    query = """
    SELECT attempts_array, range_min, range_max, number_to_guess
    FROM game_stats
    WHERE attempts_array IS NOT NULL
    AND user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
    """
    
    # Load raw data
    df_raw = pd.read_sql_query(query, conn)
    conn.close()
    
    # Process the data into a format suitable for ML
    processed_data = []
    
    for _, row in df_raw.iterrows():
        attempts = json.loads(row['attempts_array'])
        range_min = row['range_min']
        range_max = row['range_max']
        target = row['number_to_guess']
        
        # Process each attempt except the last one
        for i in range(len(attempts) - 1):
            current_guess = attempts[i]
            next_guess = attempts[i + 1]
            attempt_count = i + 1
            
            # Determine feedback (-1 for "less", 1 for "more")
            if current_guess > target:
                feedback = -1  # need to guess lower
            elif current_guess < target:
                feedback = 1   # need to guess higher
            else:
                feedback = 0   # correct guess
            
            processed_data.append({
                'range_start': range_min,
                'range_end': range_max,
                'last_guess': current_guess,
                'attempt_count': attempt_count,
                'feedback': feedback,
                'next_guess': next_guess
            })
    
    return pd.DataFrame(processed_data)

def prepare_data(df):
    # Define features and target
    X = df[['range_start', 'range_end', 'last_guess', 'attempt_count', 'feedback']]
    y = df['next_guess']
    
    # Split the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    return X_train, X_test, y_train, y_test

def train_model(X_train, y_train):
    # Initialize and train the Random Forest model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    # Make predictions on the test set
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Mean Squared Error: {mse:.2f}")
    print(f"R² Score: {r2:.2f}")
    
    return y_pred

def predict_next_guess(model, range_start, range_end, last_guess, attempt_count, feedback):
    # Create input features for prediction as a DataFrame with named columns
    features = pd.DataFrame([[range_start, range_end, last_guess, attempt_count, feedback]], 
                          columns=['range_start', 'range_end', 'last_guess', 'attempt_count', 'feedback'])
    
    # Make prediction
    prediction = model.predict(features)[0]
    
    # Ensure prediction stays within the valid range
    prediction = max(range_start, min(range_end, prediction))
    return int(round(prediction))


def initialize_model():
    # Load and prepare data
    print("Loading and processing data...")
    df = load_and_process_data()
    
    # Check if there are at least 10 games
    if len(df) < 10:
        raise ValueError("Not enough data available for training the model. At least 10 games are required.")
    
    print("\nPreparing data...")
    X_train, X_test, y_train, y_test = prepare_data(df)
    
    # Train and return the model
    model = train_model(X_train, y_train)
    return model

def main():
    # Load and prepare data
    print("Loading and processing data...")
    df = load_and_process_data()
    
    print("\nPreparing data...")
    X_train, X_test, y_train, y_test = prepare_data(df)
    
    # Train the model
    print("\nTraining model...")
    model = train_model(X_train, y_train)
    
    # Evaluate the model
    print("\nEvaluating model...")
    y_pred = evaluate_model(model, X_test, y_test)
    
    # Example prediction
    print("\nExample prediction:")
    sample_prediction = predict_next_guess(
        model,
        range_start=1,
        range_end=100,
        last_guess=50,
        attempt_count=1,
        feedback=-1  # -1 means the guess was too high
    )
    print(f"Predicted next guess: {sample_prediction}")

if __name__ == "__main__":
    main()
