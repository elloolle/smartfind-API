## Subscription Statuses

### **incomplete**
Occurs when the initial payment attempt fails for `collection_method=charge_automatically`.  
In this state, only `metadata` and `default_source` can be updated.

---

### **incomplete_expired**
Happens when the first invoice isn't paid within **23 hours** after entering `incomplete` status.  
This is **terminal** — the open invoice is voided and no further invoices will be generated.

---

### **trialing**
The subscription is in a **trial period**.  
It moves to `active` when the trial ends.

---

### **active**
The subscription is in **good standing**.  
- For `charge_automatically` subscriptions — after the first invoice is successfully paid.  
- For `trialing` subscriptions — when the trial ends with successful payment.

---

### **past_due**
- For `charge_automatically`: payment is required but fails.  
- For `send_invoice`: an invoice wasn't paid by the due date.

---

### **canceled**
- For `charge_automatically`: occurs after all payment retry attempts are exhausted (based on your settings).  
- For `send_invoice`: occurs if still unpaid after an additional deadline.

---

### **unpaid**
A **terminal state**, alternative to `canceled` (depending on settings).  
Payment retries are exhausted.  
New invoices may still be *created* but will be immediately **closed**.

---

### **paused**
Occurs when a **trial ends without a payment method**.  
Paused subscriptions do **not** generate invoices and can be resumed once a payment method is added.

### Test cards
https://docs.stripe.com/testing#declined-payments 
4000000000000002 - decline
4000000000000341 - accept and after decline all payments
4242424242424242 - accept