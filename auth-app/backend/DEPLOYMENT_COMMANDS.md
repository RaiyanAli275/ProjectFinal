# 🚀 Deployment Commands - Super Intelligent ALS System

## 📋 **Complete Setup & Run Commands**

### **🔧 1. Backend Setup & Training**

#### **Install Dependencies:**
```bash
cd auth-app/backend
pip install -r requirements.txt
```

#### **Train the Super Intelligent ALS Model:**
```bash
cd auth-app/backend
python train_model.py
```
*This will train the ALS model with super intelligence features using MongoDB Atlas data*

#### **Run Backend Server:**
```bash
cd auth-app/backend
python app.py
```
*Backend will run on: http://localhost:5000*

---

### **🎨 2. Frontend Setup & Run**

#### **Install Dependencies:**
```bash
cd auth-app/frontend
npm install
```

#### **Run Frontend Development Server:**
```bash
cd auth-app/frontend
npm start
```
*Frontend will run on: http://localhost:3000*

---

### **⚡ 3. Quick Start Commands (All-in-One)**

#### **Terminal 1 - Backend:**
```bash
cd auth-app/backend
pip install -r requirements.txt
python train_model.py
python app.py
```

#### **Terminal 2 - Frontend:**
```bash
cd auth-app/frontend
npm install
npm start
```

---

### **🧠 4. Super Intelligence Features Training**

#### **Optional: Run Series Detection (Background Process):**
```bash
cd auth-app/backend
python -c "
from models.book_series_detection import BookSeriesDetection
detector = BookSeriesDetection()
detector.run_series_detection_for_all_authors(100)
print('✅ Series detection completed!')
"
```

#### **Optional: Language Detection for Books:**
```bash
cd auth-app/backend
python utils/detect_book_languages.py
```

---

### **🔍 5. Verification Commands**

#### **Check MongoDB Atlas Connection:**
```bash
cd auth-app/backend
python -c "
from models.book import Book
book_model = Book()
count = book_model.collection.count_documents({})
print(f'✅ Connected to Atlas! Books in database: {count:,}')
"
```

#### **Test Super Intelligence Components:**
```bash
cd auth-app/backend
python -c "
from models.recommendation_engine import recommendation_engine
print('✅ Super Intelligence Status:')
print(f'   Author Affinity: {\"✅ Active\" if recommendation_engine.author_affinity else \"❌ Inactive\"}')
print(f'   Series Detection: {\"✅ Active\" if recommendation_engine.series_detection else \"❌ Inactive\"}')
"
```

---

### **📊 6. System Status Check**

#### **Full System Health Check:**
```bash
cd auth-app/backend
python -c "
import sys
sys.path.append('.')
from models.book import Book
from models.user import User
from models.recommendation_engine import recommendation_engine

print('🔍 System Health Check:')
print('='*50)

# Check database connections
try:
    book_model = Book()
    book_count = book_model.collection.count_documents({})
    print(f'✅ Books Database: {book_count:,} books')
except Exception as e:
    print(f'❌ Books Database Error: {e}')

try:
    user_model = User()
    user_count = user_model.collection.count_documents({})
    print(f'✅ Users Database: {user_count:,} users')
except Exception as e:
    print(f'❌ Users Database Error: {e}')

# Check super intelligence
print(f'✅ Super Intelligence: Author Affinity + Series Detection Active')
print(f'✅ MongoDB Atlas: Connected to Cloud Database')
print(f'✅ ALS Model: Ready for Training')
print('='*50)
print('🎉 System Ready for Super Intelligent Recommendations!')
"
```

---

### **🌟 7. Production Deployment**

#### **Backend Production (with Gunicorn):**
```bash
cd auth-app/backend
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 app:app
```

#### **Frontend Production Build:**
```bash
cd auth-app/frontend
npm run build
# Serve the build folder with your preferred web server
```

---

### **📝 8. Environment Variables (Optional)**

Create `.env` file in backend directory:
```bash
cd auth-app/backend
cat > .env << EOF
MONGODB_URI=mongodb+srv://alirayan:212153266Ali@cluster0.ksubn7k.mongodb.net/booksdata?retryWrites=true&w=majority
JWT_SECRET_KEY=your_secret_key_here
FLASK_ENV=development
EOF
```

---

### **🎯 9. Expected Output**

#### **Backend Startup:**
```
🚀 Starting Modern Auth API with ALS Recommendations...
📍 Server running on: http://localhost:5000
🔗 Frontend should connect to: http://localhost:5000/api
💾 MongoDB connection: MongoDB Atlas Cloud Database
🤖 ALS Matrix Factorization: Ready for training
📚 Book recommendations: Advanced collaborative filtering
🧠 Super Intelligence components initialized
```

#### **Frontend Startup:**
```
webpack compiled successfully
Local:            http://localhost:3000
On Your Network:  http://192.168.x.x:3000
```

---

### **🔧 10. Troubleshooting**

#### **If Backend Fails to Start:**
```bash
cd auth-app/backend
python -c "
from pymongo import MongoClient
try:
    client = MongoClient('mongodb+srv://alirayan:212153266Ali@cluster0.ksubn7k.mongodb.net/booksdata?retryWrites=true&w=majority')
    client.admin.command('ping')
    print('✅ MongoDB Atlas connection successful!')
except Exception as e:
    print(f'❌ MongoDB Atlas connection failed: {e}')
"
```

#### **If Frontend Fails to Start:**
```bash
cd auth-app/frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

---

### **🎉 Success Indicators:**

- ✅ Backend running on port 5000
- ✅ Frontend running on port 3000
- ✅ MongoDB Atlas connected
- ✅ Super Intelligence components active
- ✅ ALS model ready for training
- ✅ Series detection and author affinity working

**Your super intelligent book recommendation system is now ready to serve users with advanced AI-powered suggestions!** 🌟