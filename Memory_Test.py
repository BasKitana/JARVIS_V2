history = []
while True: 
    
    user_input = input("You:")
    info = {"role": "user", "content": user_input}
    history.append (info)
    print(history)