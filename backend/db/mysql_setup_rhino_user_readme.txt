1. Open MySQL 8 command line as an admin account.
2. Run:
   SOURCE C:/xampp/htdocs/rhino/backend/db/mysql_setup_rhino_user.sql;
3. Before running, replace CHANGE_THIS_PASSWORD in the SQL file with a real password.
4. Then update backend/.env to:
   DATABASE_URL=mysql+pymysql://rhino_app:YOUR_PASSWORD@localhost:3306/rhino_gene?charset=utf8mb4
   MYSQL_USER=rhino_app
   MYSQL_PASSWORD=YOUR_PASSWORD
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DB=rhino_gene
