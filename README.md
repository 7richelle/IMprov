***IMprov***

IMprov is a self-improvement app that improves growth through action. With IMprov, you can generate a random task every day to help you develop better habits and stay motivated. Make every moment an opportunity to better yourself. **Improve** yourself with **IMprov**.

---

**Tech Stack**
- **Frontend**: HTML and CSS
- **Backend**: Django
- **Database**: Supabase
- **Development Tools**: VS Code

---

**Setup**
1. Ensure Python and Git are installed.
2. Clone the repository into your local device using `git clone https://github.com/7richelle/CSIT327-G6-IMprov.git`.
3. Go one folder down by typing `cd self_productivity` into your terminal.
4. Set up and activate a virtual environment.
   - Windows:
       * `python -m venv env`
       * `env\Scripts\activate`
   - Linux / Max:
       * `python3 -m venv env`
       * `source venv/bin/activate`
5. Apply database migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`

---

**Running the Server**
1. Ensure that the virtual environment is running.
2. Run `python manage.py runserver`.
3. Enter the server link that the terminal gives you into your browser (i.e. `http://127.0.0.1:8000/`)
