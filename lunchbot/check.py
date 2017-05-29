

def log_menu(message):
    print(message)


if __name__ == '__main__':
    from .main import main

    main(args=['--verbose'], post_menu=log_menu)
