from flask import Blueprint, request, jsonify
import stripe
import os
from datetime import datetime

payments_bp = Blueprint('payments', __name__)

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Subscription tiers with correct pricing
SUBSCRIPTION_TIERS = {
    'free': {
        'name': 'Free Plan',
        'price': 0,
        'credits': 1000,
        'agents': 3,
        'features': ['Basic AI collaboration', '3 AI agents', '1,000 credits/month'],
        'stripe_price_id': None
    },
    'basic': {
        'name': 'Basic Plan',
        'price': 19,
        'credits': 5000,
        'agents': 10,
        'features': ['All 10 AI agents', '5,000 credits/month', 'Human Simulator', 'Basic relay modes'],
        'stripe_price_id': os.getenv('STRIPE_BASIC_PRICE_ID')
    },
    'professional': {
        'name': 'Professional Plan',
        'price': 99,
        'credits': 25000,
        'agents': 20,
        'features': ['All 20 AI agents', '25,000 credits/month', 'Revolutionary relay system', 'Expert Panel mode', 'Conference Chain mode', 'HTML reports'],
        'stripe_price_id': os.getenv('STRIPE_PRO_PRICE_ID')
    },
    'expert': {
        'name': 'Expert Plan',
        'price': 499,
        'credits': 100000,
        'agents': 20,
        'features': ['Everything in Professional', '100,000 credits/month', 'Personal clone training', 'Priority support', 'Custom integrations'],
        'stripe_price_id': os.getenv('STRIPE_EXPERT_PRICE_ID')
    }
}

@payments_bp.route('/plans', methods=['GET'])
def get_subscription_plans():
    """Get all subscription plans"""
    try:
        return jsonify({
            'status': 'success',
            'plans': SUBSCRIPTION_TIERS,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@payments_bp.route('/create-checkout', methods=['POST'])
def create_checkout_session():
    """Create Stripe checkout session"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        email = data.get('email', 'user@example.com')
        
        if not plan_id:
            return jsonify({'status': 'error', 'message': 'Plan ID is required'}), 400
        
        if plan_id not in SUBSCRIPTION_TIERS:
            return jsonify({'status': 'error', 'message': 'Invalid plan ID'}), 400
        
        plan = SUBSCRIPTION_TIERS[plan_id]
        
        # Handle free plan
        if plan_id == 'free':
            return jsonify({
                'status': 'success',
                'plan_id': plan_id,
                'message': 'Free plan activated',
                'redirect_url': None,
                'free_plan': True
            })
        
        # Create Stripe checkout session for paid plans
        if not plan['stripe_price_id']:
            return jsonify({'status': 'error', 'message': 'Stripe price ID not configured for this plan'}), 500
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': plan['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://thepromptlink.netlify.app/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://thepromptlink.netlify.app/cancel',
            customer_email=email,
            metadata={
                'plan_id': plan_id,
                'plan_name': plan['name']
            }
        )
        
        return jsonify({
            'status': 'success',
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
            'plan_id': plan_id,
            'plan_name': plan['name'],
            'price': plan['price']
        })
        
    except stripe.error.StripeError as e:
        return jsonify({'status': 'error', 'message': f'Stripe error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not endpoint_secret:
            return jsonify({'status': 'error', 'message': 'Webhook secret not configured'}), 500
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            plan_id = session['metadata'].get('plan_id')
            customer_email = session['customer_email']
            
            # Here you would typically:
            # 1. Update user's subscription in your database
            # 2. Grant access to the subscribed features
            # 3. Send confirmation email
            
            print(f"Subscription activated: {customer_email} -> {plan_id}")
            
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            customer_id = invoice['customer']
            
            # Handle successful recurring payment
            print(f"Payment succeeded for customer: {customer_id}")
            
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice['customer']
            
            # Handle failed payment
            print(f"Payment failed for customer: {customer_id}")
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@payments_bp.route('/verify-session', methods=['POST'])
def verify_checkout_session():
    """Verify completed checkout session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'status': 'error', 'message': 'Session ID is required'}), 400
        
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            plan_id = session.metadata.get('plan_id')
            plan = SUBSCRIPTION_TIERS.get(plan_id)
            
            return jsonify({
                'status': 'success',
                'payment_status': 'paid',
                'plan_id': plan_id,
                'plan_name': plan['name'] if plan else 'Unknown',
                'customer_email': session.customer_email,
                'subscription_active': True
            })
        else:
            return jsonify({
                'status': 'pending',
                'payment_status': session.payment_status,
                'subscription_active': False
            })
            
    except stripe.error.StripeError as e:
        return jsonify({'status': 'error', 'message': f'Stripe error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@payments_bp.route('/customer-portal', methods=['POST'])
def create_customer_portal():
    """Create customer portal session for subscription management"""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        
        if not customer_id:
            return jsonify({'status': 'error', 'message': 'Customer ID is required'}), 400
        
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url='https://thepromptlink.netlify.app/account'
        )
        
        return jsonify({
            'status': 'success',
            'portal_url': portal_session.url
        })
        
    except stripe.error.StripeError as e:
        return jsonify({'status': 'error', 'message': f'Stripe error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@payments_bp.route('/usage', methods=['GET'])
def get_usage_stats():
    """Get user usage statistics"""
    try:
        # This would typically fetch from your database
        # For now, return mock data
        return jsonify({
            'status': 'success',
            'usage': {
                'credits_used': 1250,
                'credits_remaining': 3750,
                'credits_total': 5000,
                'current_plan': 'basic',
                'billing_cycle_start': '2024-01-01',
                'billing_cycle_end': '2024-01-31',
                'agents_available': 10,
                'revolutionary_features': True
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

