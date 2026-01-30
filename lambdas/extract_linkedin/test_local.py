from handler import lambda_handler

if __name__ == "__main__":
    event = {
        "profile_url": "https://www.linkedin.com/in/lennyrachitsky/",
        "count": 5
    }

    result = lambda_handler(event, None)
    print(result)
