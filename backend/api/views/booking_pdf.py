from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
import io
from django.http import FileResponse
from ..utils.pdf_generator import get_booking_data, generate_booking_pdf

@api_view(['GET'])
def download_booking_pdf(request, awb):
    """
    Generate and return Booking Receipt PDF
    """
    try:
        # Get booking data
        booking_data = get_booking_data(awb)
        
        if not booking_data:
            return Response(
                {"error": "Booking not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Generate PDF
        pdf_buffer = generate_booking_pdf(booking_data)
        
        if not pdf_buffer:
            return Response(
                {"error": "Failed to generate PDF"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Return as FileResponse
        response = FileResponse(
            io.BytesIO(pdf_buffer), 
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="Booking_{awb}.pdf"'
        return response
        
    except Exception as e:
        print(f"Error generating Booking PDF: {e}")
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
