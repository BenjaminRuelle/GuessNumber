import sqlite3
import pandas as pd
from bokeh.layouts import column, row, grid
from bokeh.plotting import figure, show, save, output_file
from bokeh.models import ColumnDataSource, HoverTool, ColorBar, LinearColorMapper, NumeralTickFormatter
from bokeh.transform import transform
from bokeh.palettes import Spectral6, RdYlBu11
import json
from datetime import datetime
import numpy as np

# Connect to the database
conn = sqlite3.connect('guessNumber.db')

# Create a single HTML output file for all plots
output_file("game_analytics.html")

# 1. Heatmap of Number Distribution
query1 = """
SELECT number_to_guess, COUNT(*) as frequency
FROM game_stats
WHERE user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
GROUP BY number_to_guess
"""
df_numbers = pd.read_sql_query(query1, conn)

p1 = figure(width=800, height=400, title="Number Distribution Heatmap")
source = ColumnDataSource(df_numbers)
mapper = LinearColorMapper(palette=RdYlBu11, low=df_numbers['frequency'].min(), 
                         high=df_numbers['frequency'].max())

p1.vbar(x='number_to_guess', top='frequency', width=0.8, source=source,
        fill_color=transform('frequency', mapper))
p1.add_tools(HoverTool(tooltips=[
    ('Number', '@number_to_guess'),
    ('Frequency', '@frequency')
]))
p1.xaxis.axis_label = 'Number to Guess'
p1.yaxis.axis_label = 'Frequency'

# 2. First Guess Analysis
query2 = """
SELECT 
    JSON_EXTRACT(attempts_array, '$[0]') as first_guess,
    number_to_guess
FROM game_stats
WHERE user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
"""
df_first_guess = pd.read_sql_query(query2, conn)
df_first_guess['first_guess'] = df_first_guess['first_guess'].astype(float)

p2 = figure(width=800, height=400, title="First Guess vs Actual Number")
source = ColumnDataSource(df_first_guess)
p2.scatter('number_to_guess', 'first_guess', source=source)
p2.line([0, df_first_guess[['number_to_guess', 'first_guess']].max().max()], 
        [0, df_first_guess[['number_to_guess', 'first_guess']].max().max()], 
        line_color='red', line_dash='dashed')
p2.add_tools(HoverTool(tooltips=[
    ('Actual Number', '@number_to_guess'),
    ('First Guess', '@first_guess')
]))
p2.xaxis.axis_label = 'Actual Number'
p2.yaxis.axis_label = 'First Guess'

# 3. Success by Range Size
query3 = """
SELECT 
    (range_max - range_min) as range_size,
    AVG(CASE WHEN won = 1 THEN 1.0 ELSE 0.0 END) as win_rate
FROM game_stats
WHERE user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
GROUP BY range_size
"""
df_range = pd.read_sql_query(query3, conn)

p3 = figure(width=800, height=400, title="Win Rate by Range Size")
source = ColumnDataSource(df_range)
p3.line('range_size', 'win_rate', line_width=2, source=source)
p3.scatter('range_size', 'win_rate', size=8, source=source)
p3.add_tools(HoverTool(tooltips=[
    ('Range Size', '@range_size'),
    ('Win Rate', '@win_rate{0.0%}')
]))
p3.xaxis.axis_label = 'Range Size'
p3.yaxis.axis_label = 'Win Rate'
p3.yaxis.formatter = NumeralTickFormatter(format='0.0%')

# 4. Guess Distribution
query4 = """
SELECT difficulty, attempts_count
FROM game_stats
WHERE won = 1
AND user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
"""
df_dist = pd.read_sql_query(query4, conn)

p4 = figure(width=800, height=400, title="Attempts Distribution by Difficulty")

# Define colors for each difficulty
difficulty_colors = {
    'easy': '#2ECC71',    # Green
    'medium': '#F1C40F',  # Yellow
    'hard': '#E74C3C'     # Red
}

for difficulty in df_dist['difficulty'].unique():
    df_diff = df_dist[df_dist['difficulty'] == difficulty]
    hist, edges = np.histogram(df_diff['attempts_count'], bins=20)
    source = ColumnDataSource(data=dict(
        top=hist,
        left=edges[:-1],
        right=edges[1:]
    ))
    p4.quad(top='top', bottom=0, left='left', right='right',
            fill_color=difficulty_colors[difficulty],
            fill_alpha=0.6,
            line_color='black',
            line_alpha=0.3,
            legend_label=difficulty.capitalize(),
            source=source)

p4.legend.click_policy = "hide"
p4.legend.location = "top_right"
p4.legend.title = "Difficulty"
p4.legend.border_line_color = "black"
p4.legend.border_line_alpha = 0.3
p4.legend.background_fill_alpha = 0.6
p4.xaxis.axis_label = 'Number of Attempts'
p4.yaxis.axis_label = 'Number of Games'

# 5. Streak Analysis with player colors (yellow to red)
query5 = """
SELECT 
    u.email,
    g.timestamp,
    g.won,
    SUM(CASE WHEN g.won = 1 THEN 1 ELSE 0 END) 
        OVER (PARTITION BY u.id ORDER BY g.timestamp) as cumulative_wins
FROM game_stats g
JOIN users u ON g.user_id = u.id
WHERE g.user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
"""
df_streak = pd.read_sql_query(query5, conn)
df_streak['timestamp'] = pd.to_datetime(df_streak['timestamp'])

p5 = figure(width=800, height=400, x_axis_type="datetime", 
           title="Cumulative Wins Over Time")

# Get final win count for each player to determine color
final_wins = df_streak.groupby('email')['cumulative_wins'].max()
max_wins = final_wins.max()

# Create color mapper for players based on their total wins
# Yellow (#F1C40F) to Red (#E74C3C)
player_colors = {
    email: f'#{255:02x}' + 
           f'{int(196 - (wins/max_wins) * 123):02x}' + 
           f'{int(15 - (wins/max_wins) * 15):02x}'  # This creates a gradient from yellow to red
    for email, wins in final_wins.items()
}

for email in df_streak['email'].unique():
    df_player = df_streak[df_streak['email'] == email]
    source = ColumnDataSource(df_player)
    p5.line('timestamp', 'cumulative_wins', line_width=2,
            color=player_colors[email],  # Assign color based on total wins
            legend_label=f"{email} ({int(final_wins[email])} wins)", 
            source=source)

p5.add_tools(HoverTool(tooltips=[
    ('Player', '@email'),
    ('Date', '@timestamp{%F}'),
    ('Wins', '@cumulative_wins')
], formatters={"@timestamp": "datetime"}))

p5.legend.click_policy="hide"
p5.xaxis.axis_label = 'Date'
p5.yaxis.axis_label = 'Cumulative Wins'

# 6. Range vs Success Rate
query6 = """
SELECT 
    range_min, 
    range_max,
    AVG(CASE WHEN won = 1 THEN 1.0 ELSE 0.0 END) as success_rate
FROM game_stats
WHERE user_id != (
        SELECT id 
        FROM users 
        WHERE email = 'ai.player@game.com'
    )
GROUP BY range_min, range_max
"""
df_range_success = pd.read_sql_query(query6, conn)

p6 = figure(width=800, height=400, title="Success Rate by Range")
source = ColumnDataSource(df_range_success)

# Update color mapping to use red-to-green scale
color_mapper = LinearColorMapper(
    palette=['#E74C3C', '#F1C40F', '#2ECC71'],  # Red -> Yellow -> Green
    low=0,
    high=1
)

p6.scatter('range_min', 'range_max', size=20,
         color=transform('success_rate', color_mapper),
         source=source)

# Add a color bar
color_bar = ColorBar(
    color_mapper=color_mapper,
    label_standoff=12,
    border_line_color=None,
    location=(0,0),
    title='Win Rate',
    formatter=NumeralTickFormatter(format='0%')
)

p6.add_layout(color_bar, 'right')
p6.add_tools(HoverTool(tooltips=[
    ('Min', '@range_min'),
    ('Max', '@range_max'),
    ('Success Rate', '@success_rate{0.0%}')
]))
p6.xaxis.axis_label = 'Minimum Range'
p6.yaxis.axis_label = 'Maximum Range'

# Win Rate Comparison
query_win_rate = """
SELECT 
    CASE 
        WHEN user_id = (SELECT id FROM users WHERE email = 'ai.player@game.com') THEN 'AI'
        ELSE u.email 
    END as player,
    AVG(CASE WHEN won = 1 THEN 1.0 ELSE 0.0 END) as win_rate
FROM game_stats g
JOIN users u ON g.user_id = u.id
GROUP BY player
"""

df_win_rate = pd.read_sql_query(query_win_rate, conn)

p_win_rate = figure(x_range=df_win_rate['player'], title="Win Rate Comparison",
                    x_axis_label='Player', y_axis_label='Win Rate', width=800, height=400)

p_win_rate.vbar(x='player', top='win_rate', width=0.9, source=ColumnDataSource(df_win_rate),
                fill_color=transform('win_rate', LinearColorMapper(palette=RdYlBu11, low=0, high=1)))

p_win_rate.yaxis.formatter = NumeralTickFormatter(format='0.0%')
p_win_rate.add_tools(HoverTool(tooltips=[('Player', '@player'), ('Win Rate', '@win_rate{0.0%}')]))

# Query to select games for benjaminruelle42@gmail.com and ai.player@game.com with the same target value and matching timestamps
query_games = """
SELECT
    g.user_id,
    g.number_to_guess,
    JSON_EXTRACT(g.attempts_array, '$') as attempts_array,
    g.timestamp,
    u.email,
    g2.number_to_guess AS ai_number_to_guess,
    g2.timestamp AS ai_timestamp
FROM game_stats g
JOIN users u ON g.user_id = u.id
JOIN game_stats g2 ON g.timestamp = g2.timestamp
WHERE g2.user_id = (SELECT id FROM users WHERE email = 'ai.player@game.com')
AND g.user_id = (SELECT id FROM users WHERE email = 'player1@test.com')
UNION ALL  -- Include both player's and AI's data
SELECT
    g2.user_id,
    g2.number_to_guess,
    JSON_EXTRACT(g2.attempts_array, '$') as attempts_array,
    g2.timestamp,
    u2.email,
    g2.number_to_guess AS ai_number_to_guess,
    g2.timestamp AS ai_timestamp
FROM game_stats g2
JOIN users u2 ON g2.user_id = u2.id
WHERE g2.user_id = (SELECT id FROM users WHERE email = 'ai.player@game.com')
AND g2.timestamp IN (
    SELECT g.timestamp
    FROM game_stats g
    WHERE g.user_id = (SELECT id FROM users WHERE email = 'player1@test.com')
)
ORDER BY timestamp;
"""
df_games = pd.read_sql_query(query_games, conn)

# Prepare data for plotting
df_games['attempts_array'] = df_games['attempts_array'].apply(lambda x: json.loads(x))  # Convert JSON string to list
df_games_exploded = df_games.explode('attempts_array')  # Explode the attempts_array into separate rows

# Create a guess number for each guess after exploding
df_games_exploded['guess_number'] = df_games_exploded.groupby(['number_to_guess', 'email']).cumcount() + 1  # Create a guess number for each guess

# Group by target value to find games with the same target
grouped_games = df_games_exploded.groupby('number_to_guess')

# Plotting each guess for each game
p_guesses = figure(title="IA vs Player 1",
                   x_axis_label='Guess Number',
                   y_axis_label='Guess Value',
                   width=800, height=400, x_range=(1, df_games_exploded['guess_number'].max()))

# Colors for AI and Player
ai_color = 'blue'
player_color = 'green'

# Add lines for each game
for target_value, group in grouped_games:
    # Separate AI and Player data
    ai_data = group[group['email'] == 'ai.player@game.com']
    player_data = group[group['email'] == 'player1@test.com']
    
    # Plot AI guesses
    p_guesses.line(ai_data['guess_number'], ai_data['attempts_array'], 
                   line_width=2, color=ai_color, 
                   legend_label="AI Guesses")
    
    # Plot Player guesses
    p_guesses.line(player_data['guess_number'], player_data['attempts_array'], 
                   line_width=2, color=player_color, 
                   legend_label="Player Guesses")
    
    # Add target value as a line without a legend label
    p_guesses.line([0, player_data['guess_number'].max()], [target_value, target_value], 
                   line_color='red', line_dash='dashed')

# Set legend properties
p_guesses.legend.click_policy = "hide"  # This will now work as legends are added
p_guesses.legend.location = "top_left"  # Set legend location

# Arrange all plots in a grid
layout = grid([
    [p1, p2],
    [p3, p4],
    [p5, p6],
    [p_win_rate, p_guesses]
], sizing_mode="stretch_width")

# Save all plots to a single HTML file
save(layout)

conn.close()