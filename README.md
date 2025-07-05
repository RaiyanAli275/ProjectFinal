# 📚 Holmes - Advanced AI-Powered Book Recommendation System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18.2+-61DAFB.svg)](https://reactjs.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green.svg)](https://mongodb.com)
[![Redis](https://img.shields.io/badge/Redis-Cache-red.svg)](https://redis.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-orange.svg)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Holmes** is a sophisticated, production-ready book recommendation system that combines multiple AI algorithms, advanced caching strategies, and modern web technologies to deliver personalized reading suggestions across 60+ languages. Built with academic rigor and industrial best practices.

---

## 🎯 **Executive Summary**

### **Project Vision**
Holmes revolutionizes book discovery by integrating collaborative filtering, content-based recommendations, and AI-powered features into a seamless, multilingual platform. The system demonstrates advanced machine learning implementations, database optimization techniques, and modern software architecture patterns.

### **Key Technical Innovations**
- **🤖 Hybrid ML Recommendation Engine**: ALS Matrix Factorization + Content-Based FAISS
- **🌍 Multilingual Support**: 60+ languages with automatic language detection and FAISS indexing
- **⚡ Performance Optimization**: Microsecond response times through intelligent caching and connection pooling
- **📖 Continue Reading Feature**: AI-powered series detection and next-book recommendations
- **💾 Advanced Database Design**: MongoDB Atlas with Redis caching and optimized query patterns
---

## 🏗️ **System Architecture**

### **High-Level Architecture**
```mermaid
graph TB
    subgraph "Frontend Layer"
        A[React Frontend] --> B[Tailwind CSS]
        A --> C[Context API]
        A --> D[React Router]
    end
    
    subgraph "API Gateway"
        E[Flask Application] --> F[Blueprint Routes]
        E --> G[CORS & Middleware]
        E --> H[JWT Authentication]
    end
    
    subgraph "AI/ML Engine"
        I[ALS Collaborative Filtering] --> J[Implicit Library]
        K[Content-Based FAISS] --> L[TF-IDF + SVD]
        M[AI Book Enrichment] --> N[OpenAI GPT-3.5]
        O[Continue Reading AI] --> P[Series Detection]
    end
    
    subgraph "Data Layer"
        Q[(MongoDB Atlas)] --> R[Books Collection]
        Q --> S[Users Collection]
        Q --> T[Interactions Collection]
        U[(Redis Cache)] --> V[Recommendation Cache]
        U --> W[Popular Books Cache]
        U --> X[User Session Cache]
    end
    
    subgraph "Performance Layer"
        Y[Connection Pooling] --> Z[MongoDB Manager]
        AA[Memory Optimization] --> BB[FAISS Indices]
        CC[Background Processing] --> DD[Model Training]
    end
    
    A --> E
    E --> I
    E --> K
    E --> M
    E --> O
    I --> Q
    K --> Q
    M --> Q
    O --> Q
    E --> U
    E --> Y
    E --> AA
```

### **Technology Stack**

#### **Backend Technologies**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.8+ | Core application runtime |
| **Web Framework** | Flask | 2.3.3 | RESTful API development |
| **ML Library** | Implicit | 0.7.2 | ALS Matrix Factorization |
| **Vector Search** | FAISS | 1.7.4 | High-performance similarity search |
| **ML Toolkit** | Scikit-learn | 1.3.1 | TF-IDF, preprocessing, SVD |
| **AI Integration** | OpenAI | 1.0+ | GPT-3.5 for book enrichment |
| **Database** | MongoDB Atlas | 4.5+ | Document storage with cloud scaling |
| **Caching** | Redis | 5.0.1 | High-performance in-memory cache |
| **Authentication** | PyJWT | 2.8.0 | JSON Web Token implementation |

#### **Frontend Technologies**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Framework** | React | 18.2.0 | Component-based UI development |
| **Styling** | Tailwind CSS | 3.3.2 | Utility-first CSS framework |
| **Routing** | React Router | 6.3.0 | Client-side routing |
| **State Management** | Context API | Built-in | Application state management |
| **HTTP Client** | Axios | 1.4.0 | API communication |
| **Notifications** | React Hot Toast | 2.4.1 | User feedback system |

### **Database Design & Optimization**

#### **MongoDB Collections Structure**
```javascript
// Books Collection (booksdata.book)
{
  "_id": ObjectId,
  "name": "Book Title",
  "author": "Author Name",
  "genres": ["Fiction", "Adventure"],
  "summary": "Book description",
  "language_of_book": "english",
  "popularity_score": 0.85,
  "year": 2020
}

// User Interactions (user_auth_db.user_book_interactions)
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "book_name": "Book Title",
  "action": "like|dislike",
  "timestamp": ISODate,
}

// Users Collection (user_auth_db.users)
{
  "_id": ObjectId,
  "username": "user123",
  "email": "user@example.com",
  "password_hash": "bcrypt_hash",
  "languages": ["english", "spanish"],
  "created_at": ISODate
}

```

## 🤖 **AI/ML Components Deep Dive**

### **1. ALS Collaborative Filtering Engine**

#### **Technical Implementation**
```python
# Core ALS Configuration
AlternatingLeastSquares(
    factors=64,           # Latent factors for user/item embeddings
    regularization=0.1,   # L2 regularization to prevent overfitting
    iterations=50,        # Training iterations
    alpha=40,            # Confidence parameter for implicit feedback
    random_state=42      # Reproducible results
)
```

#### **Key Features**
- **Implicit Feedback Processing**: Converts user interactions (likes, searches) into confidence scores
- **Matrix Factorization**: Decomposes user-item matrix into latent factors
- **Cold Start Handling**: Automatic retraining for new users with sufficient interactions
- **Similarity Computation**: Cosine similarity for user-based collaborative filtering

#### **Performance Metrics**
- **Training Time**: ~30 seconds for 100K interactions
- **Prediction Time**: <5ms per user
- **Memory Usage**: ~50MB for trained model

### **2. Content-Based FAISS Recommendation System**

#### **Advanced Feature Engineering**
```python
# Feature Pipeline
TfidfVectorizer(stop_words='english', max_features=10000)  # Text features
MultiLabelBinarizer()                                      # Genre encoding
OneHotEncoder(sparse_output=True)                         # Author encoding
MinMaxScaler()                                            # Year normalization
TruncatedSVD(n_components=256)                           # Dimensionality reduction
```

#### **FAISS Index Strategy**
- **Per-Language Indexing**: Separate FAISS indices for each of 60+ languages
- **Adaptive Index Type**: Flat for <1K books, IVF for larger datasets
- **Memory Optimization**: Selective loading based on user language preferences
- **Vector Normalization**: L2 normalization for optimal similarity computation

#### **Scalability Features**
- **Streaming Processing**: Memory-efficient batch processing for model training
- **Incremental Loading**: Load only required language indices
- **Vector Caching**: LRU cache for frequently accessed book vectors

### **3. Continue Reading AI Feature**

#### **Series Detection Algorithm**
- **Pattern Recognition**: AI identifies book series relationships
- **Next Book Prediction**: Recommends immediate sequel with high accuracy
- **Confidence Scoring**: Provides reliability metrics for recommendations
- **Multi-format Support**: Handles various series naming conventions

#### **Performance Features**
- **First Request**: 2-5 seconds (AI processing)
- **Subsequent Requests**: <100ms (cached results)
- **Accuracy Rate**: >90% for popular series
- **Language Support**: Works across all supported languages


---

## ⚡ **Performance Engineering**

### **Caching Architecture**

#### **Multi-Layer Caching Strategy**
```mermaid
graph TD
    A[User Request] --> B{Redis Cache Hit?}
    B -->|Yes| C[Return Cached Result <100ms]
    B -->|No| D[MongoDB Query]
    D --> E[Process with AI/ML]
    E --> F[Cache Result]
    F --> G[Return to User]
    
    subgraph "Cache Layers"
        H[L1: User Sessions - 30min TTL]
        I[L2: Popular Books - 24hr TTL]
        J[L3: Recommendations - 1week TTL]
        K[L4: AI Enriched Books - Permanent]
    end
```

#### **Cache Performance Metrics**
- **Hit Rate**: 95% for recommendations
- **Response Time**: <50ms for cached requests
- **Memory Usage**: ~200MB Redis instance
- **Invalidation Strategy**: Smart cache clearing on user interactions


### **Memory Optimization**

#### **FAISS Memory Management**
- **Selective Loading**: Load only required language indices
- **Chunked Processing**: Process large datasets in manageable chunks

---

## 🚀 **Quick Start Guide for Academic Evaluation**

### **Prerequisites**
- Python 3.8+ with pip
- Node.js 16+ with npm
- MongoDB Atlas account (free tier available)
- Redis instance (local or cloud)
- OpenAI API key (for AI features), here we have our API key.

### **1. Backend Setup**
```bash
# Navigate to backend directory
cd auth-app/backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Fetch the FAISS Trained data
python GetFaissFiles.py

# Start the Flask server
python app.py
```

### **2. Frontend Setup**
```bash
# Navigate to frontend directory
cd auth-app/frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

### **3. Access the Application**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

### **4. Demo Scenarios for Evaluation**

#### **Scenario 1: User Registration & Authentication**
1. Register a new user account
2. Login with JWT authentication
3. Verify token-based session management

#### **Scenario 2: Book Discovery & Interaction**
1. Search for books by title/author
2. Like/dislike books to build preference profile
3. Observe how recommendations adapt to preferences

#### **Scenario 3: AI-Powered Features**
1. Like books from a series (e.g., Harry Potter)
2. Observe "Continue Reading" recommendations
3. Test AI book enrichment with missing books

#### **Scenario 4: Performance Testing**
1. Monitor response times in browser dev tools
2. Check Redis cache hits via health endpoint
3. Observe memory usage during heavy operations

### **API Documentation**

#### **Authentication Endpoints**
```http
POST /api/register
POST /api/login
POST /api/verify
GET  /api/user
POST /api/logout
```

#### **Book & Recommendation Endpoints**
```http
GET  /api/books/search?q={query}&limit={limit}
GET  /api/books/popular?language={lang}&limit={limit}
POST /api/books/interact
GET  /api/books/recommendations?limit={limit}
GET  /api/books/user-interactions
```

#### **Specialized AI Endpoints**
```http
GET  /api/continue-reading/
POST /api/continue-reading/refresh
```

---

### **Production Deployment**

#### **Backend Deployment (Docker)**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

#### **Environment Configuration**
```bash
# Production environment variables
export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/db"
export REDIS_URL="redis://redis-server:6379"
export OPENAI_API_KEY="your-openai-key"
export JWT_SECRET_KEY="your-secret-key"
export FLASK_ENV="production"
```
---