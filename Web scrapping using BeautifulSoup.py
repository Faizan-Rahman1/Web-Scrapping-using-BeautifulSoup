# Importing necessary libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re


# Function to parse time string to hours, as it can be in different formats
def parse_time_to_hours(time_str):
    """
    Parses the time string to extract hours.
    """
    if 'PT' in time_str:
        # Check if prep time format is PTXXM or PTXXH
        # where XX is the number of minutes or hours stored as a group
        # The return statements will convert the time to hours as a decimal, each depending on the format
        match = re.search(r'PT(\d+)H(\d+)M', time_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return hours + minutes / 60
        match = re.search(r'PT(\d+)M', time_str)
        if match:
            minutes = int(match.group(1))
            return minutes / 60
        match = re.search(r'PT(\d+)H', time_str)
        if match:
            hours = int(match.group(1))
            return hours
    else:
        # Assume format is HH:MM
        match = re.search(r'(\d+):(\d+)', time_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return hours + minutes / 60
    # Return 0 if no match found
    return 0


# Function to find the maximum value less than 10 in a list
# This is used to get the maximum time for the cooking time.
# The reason why it's maximum less than 10, is from observations, the cooking time is usually at its lowest, 10 minutes,
# so anything below 10 would be in hours and that's how we filtered the hours out, and as far as we know it works.
def max_less_than_10(numbers):
    # Filter the list to include only integers less than 10
    filtered_numbers = [num for num in numbers if num < 10]
    # Return the maximum value from the filtered list
    if filtered_numbers:
        return max(filtered_numbers)
    else:
        return None


def collect_page_data(url):
    try:
        # Fetch the webpage content
        response = requests.get(url)
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Check if the URL is from BBC website
        if not 'bbc.co.uk/food/recipes' in url:
            # Make sure the URL is from the BBC Food recipe pages and not the main page
            if 'bbc.co.uk/food' in url:
                raise ValueError("The provided URL is from the BBC Food website, but not a recipe URL.")
            else:
                raise ValueError("The provided URL is not from the BBC Food website.")

        # Extracting JSON data
        json_data = soup.find('script', type='application/ld+json').text
        recipe_data = json.loads(json_data)

        # Extracting required details from JSON
        image = recipe_data.get('image', ['N/A'])[0]
        ingredients = '\n'.join(recipe_data.get('recipeIngredient', ['N/A']))
        rating_val = recipe_data.get('aggregateRating', {}).get('ratingValue', 'N/A')
        rating_count = recipe_data.get('aggregateRating', {}).get('ratingCount', 'N/A')
        category = recipe_data.get('recipeCategory', 'N/A')
        cuisine = recipe_data.get('recipeCuisine', 'N/A')
        diet = recipe_data.get('suitableForDiet', [])

        # Check if the diet is vegan
        pattern_vegan = re.compile(r'https?://schema\.org/VeganDiet')
        # Check if the diet is vegetarian
        pattern_vegetarian = re.compile(r'https?://schema\.org/VegetarianDiet')
        if not diet:
            vegan = False
            vegetarian = False
        else:
            # If the diet is vegan, it is also vegetarian
            if any(pattern_vegan.match(d) for d in diet):
                vegan = True
                vegetarian = True
            # If the diet is vegetarian, it is not vegan
            elif any(pattern_vegetarian.match(d) for d in diet):
                vegan = False
                vegetarian = True
            # The diet is neither vegan nor vegetarian
            else:
                vegan = False
                vegetarian = False

        # Convert boolean values to Yes/No strings
        if vegan:
            vegan = 'Yes'
        else:
            vegan = 'No'
        if vegetarian:
            vegetarian = 'Yes'
        else:
            vegetarian = 'No'

        # Format rating value to 0.5 increments
        if rating_val != 'N/A':
            rating_val = f"{round(float(rating_val) / 0.5) * 0.5:.1f} stars"

        # Extracting HTML details
        title = soup.find('h1', class_='gel-trafalgar content-title__text').text.strip() if soup.find('h1', class_='gel-trafalgar content-title__text') else 'N/A'
        cook_time = soup.find('p', class_='recipe-metadata__cook-time').text.strip()
        prep_time_output = soup.find('p', class_='recipe-metadata__prep-time').text.strip()
        prep_time = recipe_data.get('prepTime', 'N/A')

        # Convert time strings to hours
        prep_time_hours = parse_time_to_hours(prep_time)

        # Extracting numeric values from cook time and converting to hours
        cook_time_values = re.findall(r'\d+', cook_time)
        # Check if there is only one value
        # If there is only one value, it is in minutes
        if len(cook_time_values) == 1:
            # Convert single value directly to hours
            cook_time_hours = int(cook_time_values[0]) / 60
        else:
            # Find the maximum value less than 10 in the list for the hours value
            cook_time_hours = max_less_than_10([int(value) for value in cook_time_values])

        # Find the maximum time from both cooking and prep time
        total_time_hours = cook_time_hours + prep_time_hours
        hours = int(total_time_hours)
        # Convert the decimal part to minutes
        minutes = int((total_time_hours - hours) * 60)
        total_time_h_and_m = f"{hours} hours and {minutes} minutes"

        # Constructing the dictionary to create the DataFrame
        data = {
            'title': [title],
            'prep_time': [prep_time_output],
            'cooking_time': [cook_time],
            'total_time_hours': [total_time_h_and_m],
            'image': [image],
            'ingredients': [ingredients],
            'rating_val': [rating_val],
            'rating_count': [rating_count],
            'category': [category],
            'cuisine': [cuisine],
            'diet': [diet],
            'vegan': [vegan],
            'vegetarian': [vegetarian],
            'url': [url]
        }

        # Creating the DataFrame
        df = pd.DataFrame(data)

        # Saving to CSV
        df.to_csv('recipe_data.csv', index=False)
        return df
    # Exception handling to allow all type of data so that it doesn't crash
    except requests.RequestException:
        print(f"Failed to fetch the webpage")
        return None

    except ValueError as e:
        print(f"Invalid URL: {e}")
        return None


# Test Cases
url1 = 'https://www.bbc.co.uk/food/recipes/quick_fish_gratin_07463'
url2 = 'https://www.bbc.co.uk/food/recipes/easiest_ever_banana_cake_42108'
url3 = 'https://www.bbc.co.uk/food/recipes/barbecue_pulled_chicken_47216'
df = collect_page_data(url3)
# Print the DataFrame if it can create one with valid data
if df is not None:
    print(df)
