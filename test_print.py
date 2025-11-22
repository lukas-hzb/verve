with open("test_output_python.txt", "w") as f:
    f.write("Hello from test_print.py writing to file\n")
    try:
        import app
        f.write("Imported app successfully\n")
    except Exception as e:
        f.write(f"Failed to import app: {e}\n")
