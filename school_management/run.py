"""Start the School Management System.

    python run.py            -> open http://localhost:5000 in your browser
    python run.py --demo     -> same, but first loads sample data into an empty system
    python run.py --network  -> let other computers on the school network connect too
"""
import argparse
import threading
import webbrowser

from school import create_app


def main():
    parser = argparse.ArgumentParser(description="School Management System")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--network", action="store_true",
                        help="allow other computers on the same network (LAN) to use the system")
    parser.add_argument("--demo", action="store_true", help="load sample data if the system is empty")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser automatically")
    args = parser.parse_args()

    app = create_app()
    if args.demo:
        with app.test_request_context():
            from school.db import scalar
            from school.demo import load_demo
            if scalar("SELECT COUNT(*) FROM students") == 0:
                load_demo()
                print("Sample data loaded.")
            else:
                print("System already has students - sample data NOT loaded.")

    host = "0.0.0.0" if args.network else "127.0.0.1"
    url = f"http://localhost:{args.port}"
    print("=" * 60)
    print(" School Management System is running.")
    print(f" Open {url} in your web browser.")
    if args.network:
        print(" Other computers: use http://<this-computer's-IP>:%d" % args.port)
    print(" First login:  username  admin   password  admin123")
    print(" Keep this window open. Close it to stop the system.")
    print("=" * 60)
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    try:
        from waitress import serve  # production-quality server, if installed
        serve(app, host=host, port=args.port)
    except ImportError:
        app.run(host=host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
