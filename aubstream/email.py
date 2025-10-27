from django.core.mail import send_mail

# def send_validation_email(user_email, credit_reference):
#     send_mail(
#         subject='Nouvelle demande de validation',
#         message=f'Vous avez une nouvelle demande de validation du crédit {credit_reference}.',
#         from_email='mahmedou500@gmail.com',
#         recipient_list=[user_email],
#         fail_silently=False,
#     )

def send_validation_email(user_email, ref_fac, validateur):
    subject = f"Demande de validation - Transfert {ref_fac}"
    message = (
        f"Bonjour {validateur.post} ({validateur.fullname}),\n\n"
        f"Vous avez une nouvelle demande de validation pour le Transfert portant la référence {ref_fac}.\n"
        f"Merci de vous connecter à la plateforme pour examiner et traiter cette demande.\n\n"
        f"Cordialement,\n"
    )
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )


    
# def send_validation_email(user_email, ref_fac, validateur):
#     subject = f"Demande de validation - Transfert {credit_reference}"
#     message = (
#         f"Bonjour {validateur.post} ({validateur.username} {validateur.fullname}),\n\n"
#         f"Vous avez une nouvelle demande de validation pour le Transfert portant la référence {ref_fac}.\n"
#         f"Merci de vous connecter à la plateforme pour examiner et traiter cette demande.\n\n"
#         f"Cordialement,\n"
#     )
    
#     send_mail(
#         subject=subject,
#         message=message,
#         from_email='mahmedou500@gmail.com',
#         recipient_list=[user_email],
#         fail_silently=False,
#     )