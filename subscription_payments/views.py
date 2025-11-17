from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from dotenv import load_dotenv
import stripe

load_dotenv()
stripe.api_key = os.getenv("TEST_STRIPE_API_KEY")


class TestView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        from decimal import Decimal

        from payments import get_payment_model

        Payment = get_payment_model()
        payment = Payment.objects.create(
            variant="stripe",  # this is the variant from PAYMENT_VARIANTS
            total=Decimal(120),
            currency="USD",
        )
        try:
            payment.get_form()
        except Exception as e:
            print("-" * 50)
            print(e)
            print("-" * 50)

            return Response({"link": str(e)})
