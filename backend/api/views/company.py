from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import CompanyProfile, UserDetails
from ..middleware import CustomMiddleware
import cloudinary.uploader


class CompanyProfileAPI(APIView):
    """Get company profile for authenticated user"""
    
    def get(self, request):
        try:
            # Get user from token
            token = request.headers.get('Authorization', '').replace('Bearer ', '').replace('Token ', '')
            user = CustomMiddleware.get_user_from_token(token)
            
            if not user:
                return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user details
            user_details = UserDetails.objects.get(user=user)
            
            if not user_details.company:
                return Response({'error': 'No company profile assigned'}, status=status.HTTP_404_NOT_FOUND)
            
            company = user_details.company
            
            return Response({
                'company_code': company.company_code,
                'company_name': company.company_name,
                'logo_url': company.logo_url,
                'primary_color': company.primary_color,
                'secondary_color': company.secondary_color,
                'contact_email': company.contact_email,
                'contact_phone': company.contact_phone,
                'address': company.address,
            }, status=status.HTTP_200_OK)
            
        except UserDetails.DoesNotExist:
            return Response({'error': 'User details not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompanyLogoUploadAPI(APIView):
    """Upload company logo to Cloudinary"""
    
    def post(self, request):
        try:
            # Get user from token
            token = request.headers.get('Authorization', '').replace('Bearer ', '').replace('Token ', '')
            user = CustomMiddleware.get_user_from_token(token)
            
            if not user:
                return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user details
            user_details = UserDetails.objects.get(user=user)
            
            if not user_details.company:
                return Response({'error': 'No company profile assigned'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user has permission (admin or hub user)
            if user_details.type not in ['hub', 'admin']:
                return Response({'error': 'Unauthorized to upload logo'}, status=status.HTTP_403_FORBIDDEN)
            
            # Get logo file from request
            logo_file = request.FILES.get('logo')
            
            if not logo_file:
                return Response({'error': 'No logo file provided'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                logo_file,
                folder=f"company_logos/{user_details.company.company_code}",
                public_id=f"logo_{user_details.company.company_code}",
                overwrite=True,
                resource_type="image"
            )
            
            # Update company profile with new logo URL
            company = user_details.company
            company.logo_url = upload_result.get('secure_url')
            company.save()
            
            return Response({
                'message': 'Logo uploaded successfully',
                'logo_url': company.logo_url
            }, status=status.HTTP_200_OK)
            
        except UserDetails.DoesNotExist:
            return Response({'error': 'User details not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompanyListAPI(APIView):
    """Get list of all companies (admin only)"""
    
    def get(self, request):
        try:
            # Get user from token
            token = request.headers.get('Authorization', '').replace('Bearer ', '').replace('Token ', '')
            user = CustomMiddleware.get_user_from_token(token)
            
            if not user:
                return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user details
            user_details = UserDetails.objects.get(user=user)
            
            # Check if user is admin
            if user_details.type != 'admin':
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
            # Get all companies
            companies = CompanyProfile.objects.filter(is_active=True)
            
            companies_data = [{
                'company_code': company.company_code,
                'company_name': company.company_name,
                'logo_url': company.logo_url,
                'primary_color': company.primary_color,
                'secondary_color': company.secondary_color,
                'contact_email': company.contact_email,
                'contact_phone': company.contact_phone,
            } for company in companies]
            
            return Response({'companies': companies_data}, status=status.HTTP_200_OK)
            
        except UserDetails.DoesNotExist:
            return Response({'error': 'User details not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateCompanyProfileAPI(APIView):
    """Update company profile details"""
    
    def put(self, request):
        try:
            # Get user from token
            token = request.headers.get('Authorization', '').replace('Bearer ', '').replace('Token ', '')
            user = CustomMiddleware.get_user_from_token(token)
            
            if not user:
                return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user details
            user_details = UserDetails.objects.get(user=user)
            
            if not user_details.company:
                return Response({'error': 'No company profile assigned'}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user has permission
            if user_details.type not in ['hub', 'admin']:
                return Response({'error': 'Unauthorized to update company profile'}, status=status.HTTP_403_FORBIDDEN)
            
            company = user_details.company
            
            # Update fields if provided
            if 'company_name' in request.data:
                company.company_name = request.data['company_name']
            if 'primary_color' in request.data:
                company.primary_color = request.data['primary_color']
            if 'secondary_color' in request.data:
                company.secondary_color = request.data['secondary_color']
            if 'contact_email' in request.data:
                company.contact_email = request.data['contact_email']
            if 'contact_phone' in request.data:
                company.contact_phone = request.data['contact_phone']
            if 'address' in request.data:
                company.address = request.data['address']
            
            company.save()
            
            return Response({
                'message': 'Company profile updated successfully',
                'company': {
                    'company_code': company.company_code,
                    'company_name': company.company_name,
                    'logo_url': company.logo_url,
                    'primary_color': company.primary_color,
                    'secondary_color': company.secondary_color,
                    'contact_email': company.contact_email,
                    'contact_phone': company.contact_phone,
                    'address': company.address,
                }
            }, status=status.HTTP_200_OK)
            
        except UserDetails.DoesNotExist:
            return Response({'error': 'User details not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
