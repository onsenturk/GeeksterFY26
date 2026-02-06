# GeeksterFY26 Data Schema & Relationships (Updated)

## 📊 Dataset Classification

### Business Data (Chocolate Global & Supporting)
These datasets represent actual business/operational data suitable for analysis:

#### 1. **Cupid Chocolate Global** (Star Schema - Independent Dataset)
**Status**: Core business intelligence dataset  
**Tables**: 7 (DimCustomer, DimProduct, DimDate, DimStore, DimPromotion, DimSupplier, FactSales)  
**Size**: ~13K transactions

**Relationships within Chocolate Global**:
- FactSales → DimCustomer (via customer_id) 
- FactSales → DimProduct (via product_id)
- FactSales → DimDate (via date_id)
- FactSales → DimStore (via store_id)
- FactSales → DimPromotion (via promotion_id)
- FactSales → DimSupplier (via supplier_id)

**Cross-Dataset Relationships**:
- Connects to GIFTS via customer_id
- Connects to SUPPLY_CHAIN via product_id

---

#### 2. **Gifts** (Event Log - 10,000 records)
**Primary Key**: event_id  
**Foreign Key**: customer_id → DimCustomer (Chocolate Global)  
**Purpose**: E-commerce event tracking and recommendations  
**Key Columns**: event_type, event_ts, product_sku, rating, returned_flag, loyalty_tier

**Relationship**: Joins with Chocolate Global DimCustomer via customer_id

---

#### 3. **Supply Chain** (Operational - 100+ records)
**Primary Key**: order_id  
**Foreign Key**: product_id → DimProduct (Chocolate Global)  
**Purpose**: Inventory, logistics, and supplier management  
**Key Columns**: vendor_lead_time_days, stock_level, delay_reason, region, cost_per_unit

**Relationship**: Joins with Chocolate Global DimProduct via product_id

---

#### 4. **Work Dynamics** (Telemetry - 100 events) [UPDATED]
**Primary Key**: event_id  
**Purpose**: Workplace meeting patterns and collaboration insights  
**Key Columns**: 
- meeting_id
- participant_ids (NEW: JSON array of user IDs, e.g., ["U0001", "U0042", "U0087"])
- response_pattern (accepted/declined/tentative/ghosted)
- cross_timezone_issues
- sentiment_of_notes
- action_items_completed

**Note**: This dataset is INDEPENDENT - participants refer to work environment users, not Chocolate Global customers

---

### Application Telemetry Data (Keep Separate)
These datasets represent platform/application-level events and should be treated as independent:

#### 5. **Matchmaking** (User Profiles - 100 users)
**Primary Key**: user_id  
**Purpose**: User profiles and relationship potential  
**Type**: Application telemetry - DO NOT connect to business data

#### 6. **Behavior Edges** (Graph - 100 edges)
**Primary Key**: edge_id  
**Foreign Keys**: source_user_id, target_user_id → Matchmaking  
**Purpose**: Social network and interaction patterns  
**Type**: Application telemetry - DO NOT connect to business data

#### 7. **Broken Hearts Security** (Audit Log - 100 records)
**Primary Key**: security_audit_id  
**Foreign Key**: user_id → Matchmaking  
**Purpose**: Authentication and security audit trail  
**Type**: Application telemetry - DO NOT connect to business data

#### 8. **Trust & Safety** (Content Moderation - 100 records)
**Primary Key**: message_id  
**Purpose**: Message moderation and safety classification  
**Type**: Application telemetry - DO NOT connect to business data

#### 9. **Global Routing** (Infrastructure - 100 records)
**Primary Key**: routing_id  
**Purpose**: Network routing and performance metrics  
**Type**: Application telemetry - DO NOT connect to business data

#### 10. **Love Notes Telemetry** (Messages - 100 records)
**Primary Key**: message_id  
**Purpose**: Message telemetry and engagement tracking  
**Type**: Application telemetry - DO NOT connect to business data

---

## 🔗 Valid Relationship Paths

### Within Business Data (Connected Star Schema):
```
GiftRecommender.customer_id → Chocolate Global.DimCustomer.customer_id
            ↓
FactSales.customer_id → DimCustomer

SupplyChain.product_id → Chocolate Global.DimProduct.product_id
            ↓
FactSales.product_id → DimProduct
```

### Independent Subgraph (Application Telemetry):
```
Matchmaking (core user dimension)
    ├→ BrokenHeartsSecurity (via user_id)
    ├→ BehaviorEdges (via source/target user_id)
    └→ LoveNotesTelemetry (implicit user context)

GlobalRouting (infrastructure)
TrustSafety (content moderation)
```

---

## ❌ Invalid Relationships (Separate Instances)

- **DO NOT** connect WorkDynamics to Matchmaking (different user contexts)
- **DO NOT** connect WorkDynamics to Chocolate Global (different domains)
- **DO NOT** connect any business data to application telemetry datasets
- **DO NOT** create relationships between infrastructure metrics and business/user data

**Rationale**: 
- Chocolate Global is business/e-commerce data
- Matchmaking & telemetry are application platform data
- Work Dynamics is workplace collaboration data
- They operate in different domains with different user populations

---

## 📋 Column Specifications

### Modern Work Dynamics (Updated Schema)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| event_id | String | Unique event identifier | EVT00001 |
| meeting_id | String | Unique meeting identifier | MTG00001 |
| participant_ids | JSON Array | Array of participating user IDs | ["U0001", "U0042", "U0087"] |
| response_pattern | String | Response to meeting (accepted/declined/tentative/ghosted) | accepted |
| cross_timezone_issues | Boolean | Whether meeting spans timezones | True/False |
| sentiment_of_notes | Float | Sentiment score of meeting notes | -0.628 to 0.947 |
| action_items_completed | Integer | Number of action items completed | 0-5 |

---

## 🎯 Implementation Guidelines

### For Analysis
1. **Business Intelligence**: Use Chocolate Global, Gifts, Supply Chain together
2. **Collaboration Analytics**: Use Work Dynamics independently
3. **Platform Insights**: Use Matchmaking, Security, Behavior, Trust/Safety together

### For Data Integration
- Join Gifts with Chocolate Global via customer_id
- Join Supply Chain with Chocolate Global via product_id
- Keep all other datasets separate unless your analysis explicitly requires cross-domain insight

### For Visualization
- Create separate dashboards for business vs. application data
- Use Work Dynamics for HR/organizational analytics
- Use platform telemetry for platform health monitoring
