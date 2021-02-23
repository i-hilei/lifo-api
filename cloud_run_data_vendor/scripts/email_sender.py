#!/usr/bin/python3

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
from datetime import datetime
import pytz
from nylas import APIClient
import random

class EmailSender():
    def __init__(self, sg_token='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', \
        nylas_client_id='', nylas_client_secret='', nylas_access_token=['g9uAzZds6zE0vtug0ZxTUMOL5hGM1e']):
        self.token = sg_token
        self.nylas_client_id = nylas_client_id
        self.nylas_client_secret = nylas_client_secret
        self.nylas_sender = nylas_access_token

    def send_nylas_email(self, from_email, to_emails, subject, from_name='Lifo Notifications', 
                        text_content=None, html_content=None, attachement=None):
        if html_content:
            content = html_content
        else:
            content = text_content
        sender_id = random.randrange(len(self.nylas_sender)) 
        nylas = APIClient(
                app_id=self.nylas_client_id,
                app_secret=self.nylas_client_secret,
                access_token=self.nylas_sender[sender_id]
            )
        try:
            draft = nylas.drafts.create()
            draft.subject = subject
            draft.body = content
            # draft.from_ = [{'email': from_email, 'name': from_name}]
            draft.to = [{'email': to_emails}]
            response = draft.send()
            print('Email sent successfully by %s' % nylas.account.email_address)
            return response
        except Exception as e:
            print(f'Sending email failed! Error message is {str(e)}')
            return None

    def send_sendgrid_email(self, from_email, to_emails, subject,
                            from_name='Lifo Notifications', text_content=None, html_content=None,
                            attachement=None):
        from_email = From(from_email, from_name)
        to_email = To(to_emails)
        subject = subject
        if html_content:
            content = Content("text/html", html_content)
        else:
            content = Content("text/plain", text_content)
        mail = Mail(from_email, to_email, subject, content)
        if attachement:
            mail.attachment = attachement
        try:
            sg = SendGridAPIClient(self.token)
            response = sg.client.mail.send.post(request_body=mail.get())
            if response.status_code < 400:
                print('Send ok')
                return mail.get()
            else:
                return None
        except Exception as e:
            print(e)
            return None

    def send_accept_discovery_email(self, to_email, account_id, product_name, campaign_id):
        title = f' Your Application for Lifo Campaign is Approved! - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>Your collaboration application for the Lifo campaign of product ‘{product_name}’ is approved! ')
        template.append(f'We’ll ship the product out to you soon and notify you via email when it’s shipped. Once it’s delivered, don’t forget to visit ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a> ')
        template.append(f'to upload your draft content and win your commission! </p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_product_shipped_email(self, to_email, account_id, product_name, campaign_id, tracking_number, carrier, delivery_window):
        title = f'Your Product for Lifo Campaign is shipped! - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>Your Lifo campaign product ‘{product_name}’ is on its way! ')
        template.append(f'You can check the progress with tracking number <b>{tracking_number}</b> (by <b>{carrier}</b>) and you will receive an email when it’s delivered. ')
        template.append(f'Please visit <a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a> ')
        template.append(f'to upload your draft content within <b>{delivery_window}</b> hours after the delivery. </p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )
    
    def send_product_deliver_email(self, to_email, account_id, product_name, campaign_id, delivery_window, bonus_dollar=0, bonus_time=0):
        title = f'Your Product for Lifo Campaign is delivered! - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>Your Lifo campaign product ‘{product_name}’ is delivered. Please visit Lifo: ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a> to upload your draft content within <b>{delivery_window}</b> hours after the delivery. ')
        if bonus_dollar > 0 and bonus_time > 0:
            template.append(f'Earn an extra bonus of ${bonus_dollar} by submitting the draft within {bonus_time} hours!')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_draft_approve_email(self, to_email, account_id, product_name, campaign_id, commission_dollar, platform='instagram'):
        title = f'Your Draft for Lifo Campaign is approved! - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>Congratulations! Your content for product ‘{product_name}’ is approved and ready to go! Please post your content to {platform} based on the campaign timeline and share the URL of your post in ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a> after it\'s live. ') 
        if commission_dollar:
            template.append(f'Once done, the commission will be issued to your Lifo account. </p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_content_remainder_email(self, to_email, account_id, product_name, campaign_id, deadline, commission_dollar):
        deadline_date = datetime.fromtimestamp(deadline, pytz.timezone('America/Los_Angeles')).strftime('%m/%d')
        deadline_time = datetime.fromtimestamp(deadline, pytz.timezone('America/Los_Angeles')).strftime('%H:%M %m/%d/%y %Z')
        title = f'Hurry up! You draft content for Lifo Campaign is due on {deadline_date} - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>This is a friendly reminder that your Lifo campaign draft content for product ‘{product_name}’ is due on <b>{deadline_time}</b>. ')
        template.append(f'Don’t forget to follow the campaign instructions and submit your content in ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a>. ')
        if commission_dollar:
            template.append(f'Otherwise, your commission may be reduced. </p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )
    
    def send_post_reminder_email(self, to_email, account_id, product_name, campaign_id, deadline, commission_dollar, platform='instagram'):
        deadline_time = datetime.fromtimestamp(deadline, pytz.timezone('America/Los_Angeles')).strftime('%H:%M %m/%d/%y %Z')
        title = f'Hurry up! Your content post for Lifo Campaign is due in 2 hrs - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'This is a friendly reminder that your Lifo campaign content post for product ‘{product_name}’ is due on <b>{deadline_time}</b>. ')
        template.append(f'Please post your content to {platform} and share the URL in ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a>. ')
        if commission_dollar:
            template.append(f'Otherwise, your commission may be reduced. </p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_content_overdue_email(self, to_email, account_id, product_name, campaign_id, campaign_deadline=0):
        title = f'Reminder: Your Draft for Lifo Campaign is overdue - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>This is a friendly reminder that your Lifo campaign draft content for product ‘{product_name}’ is overdue. ')
        template.append(f'Please follow the campaign instructions and submit your content in ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a>')        
        if campaign_deadline:
            deadline_time = datetime.fromtimestamp(campaign_deadline, pytz.timezone('America/Los_Angeles')).strftime('%H:%M %m/%d/%y %Z')
            template.append(f' before the campaign expires on <b>{deadline_time}</b>. Otherwise, your commission may be reduced.</p>')
        else:
            template.append(f'. Otherwise, your commission may be reduced.')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_post_overdue_email(self, to_email, account_id, product_name, campaign_id, campaign_deadline=0):
        title = f'Reminder: Your content post for Lifo Campaign is overdue - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>This is a friendly reminder that your Lifo campaign content post for product ‘{product_name}’ is overdue. ')
        template.append(f'Please follow the campaign instructions and post your content in ')
        template.append(f'<a href="https://influencer.lifo.ai/campaign/{campaign_id}" target="_blank">Lifo Campaign Detail Page</a>')        
        if campaign_deadline:
            deadline_time = datetime.fromtimestamp(campaign_deadline, pytz.timezone('America/Los_Angeles')).strftime('%H:%M %m/%d/%y %Z')
            template.append(f' before the campaign expires on {deadline_time}. Otherwise, your commission may be reduced.</p>')
        else:
            template.append(f'. Otherwise, your commission may be reduced. </p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_commission_issued_email(self, to_email, account_id, product_name, amount, wait_days=14):
        title = f'Your commission for Lifo campaign has been issued to your account! - Product: ‘{product_name}’'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>Your Lifo campaign commission of <b>${amount}</b> for product ‘{product_name}’ has been issued to your account. ')
        template.append(f'Please <a href="https://influencer.lifo.ai/my-earnings" target="_blank">visit Lifo</a> ')
        template.append(f'to view your account balance details and request for payout. ')
        template.append(f'Please note that it will take {wait_days} days beforefor you can request the fund to transfer to youryourto cash out to your PayPal! - Just a little bit wait :)</p>')
        template.append(f'<p>If you have any questions, please contact us at influencer@lifo.ai or call 833-800-LIFO.</p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_payment_complete_email(self, to_email, account_id, amount):
        title = f'Your Lifo payment request has been received'
        template = []
        template.append(f'<p>Hey {account_id},</p>')
        template.append(f'<p>We have received your payment request for an amount of <b>${amount}</b> to your PayPal account. ')
        template.append(f'You may receive a Paypal notification once the transfer is completed. It usually takes a few business days. </p>')
        template.append(f'<p><b>IMPORTANT: If you did not make this request or if there are any other issues, including not receiving funds, ')
        template.append(f'please contact us at influencer@lifo.ai or call 833-800-LIFO. </b></p>')
        template.append(f'<p>Cheers,<br>Team Lifo</p>')
        # Footer For security reasons, you cannot unsubscribe from transaction emails.
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails=to_email, 
            subject=title,
            html_content=''.join(template)
        )

    def send_referral_emails(self, referee_list, referral_link, referer_name, referer_email, test_email=None):
        result = []
        for user in referee_list:
            referee_name = user['instagram_id']
            referee_email = user['email']
            title = f'{referer_name} Invites You to Join Lifo and Get iPhone 12 in Our Holiday Raffle'
            template = []
            template.append(f'<p>{referer_name} ({referer_email}) has invited you to join Lifo - a community for high-quality influencers. </p>')
            template.append(f'<p><a href="{referral_link}" target="_blank">Accept invitation</a></p>')
            template.append(f'<p>Lifo is a platform connecting quality brands and influencers. Join Lifo today to unlock high quality paying campaigns and work with trusted brands. </p>')
            template.append(f'<p>Your invitation is associated with a raffle. The winner will receive <b>one IPHONE 12</b> with color of their choice. You will earn raffle tickets by signing up and collaborating with brands. Sign up today to participate.</p>')
            template.append(f'<p>See you in Lifo =)</p>')
            template.append(f'<p>The Lifo Team</p>')
            # Footer For security reasons, you cannot unsubscribe from transaction emails.
            result.append(self.send_nylas_email(
                from_email='notifications@lifo.ai', 
                from_name=f'{referer_name} via Lifo',
                to_emails=test_email if test_email is not None else referee_email, 
                subject=title,
                html_content=''.join(template)
            ))
        return result
    
    def send_book_demo_email(self, email, name, phone_number):
        title = f'New Brand Demo Request'
        template = []
        template.append(f'<p>Hey Alex,</p>')
        template.append(f'<p>{name} ({email}, {phone_number} just booked a demo.</p>')
        # template.append(f'<p>Here is additional information for the brand: </p>')
        return self.send_nylas_email(
            from_email='notifications@lifo.ai', 
            to_emails='lifo-sales@lifo.ai', 
            subject=title,
            html_content=''.join(template)
        )

    def send_invitation_email(self, instagram_id, to_email):
        title = 'Don\'t miss out! Join Lifo for Great Collaborations'
        html_content = f'''
            <p>Hi {instagram_id},</p>
            <p>You may have received influencer campaign requests or have worked with Lifo in the past. We loved your profile and would like to extend an invitation to you to <a href="https://bit.ly/357vHQZ" target="_blank">join our Lifo platform</a>. </p>
            <p>Lifo, a fast-growing silicon valley start-up, is building a community for high-quality influencers. We find superior brands that match with your style and audience, and provide you with stable revenue streams. What differentiates Lifo from others includes - </p>
            <li><b>Commission guarantee</b> - as long as your contents follow the provided guidelines, commissions will be paid to your Lifo wallet</li>
            <li><b>Brands that you can trust</b> --we handpick quality brands and products for you to collaborate with</li>
            <li><b>Simple workflow</b> - no more back-and-forth with the brand or agent to complete a campaign. We provide clear guidelines upfront so that you can focus on content creation</li>
            <li><b>Get paid more</b> - responsive, high-quality, on time deliveries will be rewarded with higher commission rates, so that more brands would love to work with you</li>
            <li><b>You work with us directly</b> - you can always find Lifo account managers to handle any questions you might have</li>
            <p>Excited to have you onboard! </p>
            <p>Best, <br>Lifo Team</p>
        '''
        return self.send_sendgrid_email(
            from_email='notifications@lifo.ai',
            from_name='Alex from Lifo',
            to_emails=to_email,
            subject=title,
            html_content=html_content
        )

    def send_raffle_to_registered(self, instagram_id, to_email):
        title = 'Lifo Holiday Raffle On-going - Refer Your Influencer Friends and Earn The IPHONE 12'
        html_content = f'''
            <p>Hi {instagram_id},</p>
            <p>Want to win a new iPhone 12? Participate in our holiday raffle and get the chance to <a href="https://influencer.lifo.ai/lottery-information", target="bland">win a new iPhone 12</a> by referring your influencer friends. </p>
            <p>We’re hosting a series of holiday raffle events. Starting from today to Nov 15, 2020, any eligible friend referral and completion of campaign could earn extra raffle tickets to win a <b>NEW IPHONE 12</b> with your color of choice.  </p>
            <p><img src="https://firebasestorage.googleapis.com/v0/b/influencer-272204.appspot.com/o/marketing%2Flottery.png?alt=media&token=f5751e18-6ad3-46e2-8a59-3d62fa1d762a" style="max-width: 400px" /><br /></p>
            <p>Check it out in Lifo, and wish you a happy holiday =D </p>
            <p>The Lifo Team</p>
        '''
        return self.send_nylas_email(
            from_email='notifications@marketing.lifo.ai',
            from_name='Alex from Lifo',
            to_emails=to_email,
            subject=title,
            html_content=html_content
        )

    def send_raffle_to_unregistered(self, instagram_id, to_email):
        title = 'Join Lifo Influencer Community and Participate in Holiday Raffle for IPHONE 12'
        html_content = f'''
            <p>Hi {instagram_id},</p>
            <p>Want to win a new iPhone 12? <b>Join the Lifo influencer community</a>, and get the chance to <a href="https://bit.ly/3ktsQWB" target="blank">win a new iPhone 12 in our holiday raffle</a>! </p>
            <p>If you miss my previous email about what Lifo is, here is a quick recap - Lifo is building a community for high-quality influencers. We find superior brands that match with your style and audience, and provide you with stable revenue streams.</p>
            <p>We’re hosting a series of holiday raffle events. Starting from today to Nov 15, 2020, any eligible friend referral and completion of campaign could earn extra raffle tickets to win a <b>NEW IPHONE 12</b> with your color of choice.  </p>
            <p><img src="https://firebasestorage.googleapis.com/v0/b/influencer-272204.appspot.com/o/marketing%2Flottery.png?alt=media&token=f5751e18-6ad3-46e2-8a59-3d62fa1d762a" style="max-width: 400px" /><br /></p>
            <p>See you in our influencer community =) </p>
            <p>The Lifo Team</p>
        '''
        return self.send_sendgrid_email(
            from_email='notifications@marketing.lifo.ai',
            from_name='Alex from Lifo',
            to_emails=to_email,
            subject=title,
            html_content=html_content
        )

    def send_bait_email_to_unregistered(self, instagram_id, to_email):
        title = 'Find high-quality brand collaborations in Lifo influencer community'
        html_content = f'''
            <p>Hi there,</p>
            <p>This is <a href="https://influencer.lifo.ai/email">Lifo</a> -- we connect quality brands with high-quality influencers.</p>
            <p>I'm reaching out regarding several great collaboration opportunities. If you would like to be part of it, please apply by filling this quick application form <a href="https://lifo.typeform.com/to/nDkj3dsl">HERE</a>.</p>
            <p>You will be notified by email when approved. If you do not hear from us, don’t worry, check Lifo platform out, we will keep updating more exclusive high-paying collaborations for you.</p>
            <p><b>Collaboration #1 - Limited Spots Available</b></p>
            <li>Product # - 219312</li>
            <li>Product name - Mija Tyre Earring</li>
            <li>Product link - <a href="https://mijastudio.com/collections/mija-earring/products/tyre-earring">here</a></li>
            <li>Rewards - <b>$150</b></li>
            <li>Platform - <b>Instagram</b></li>
            <li>Content needed - 1 static post + 3 stories</li>
            <p><b>Collaboration #2 - Limited Spots Available</b></p>
            <li>Product # - 729004</li>
            <li>Product name - Sportneer Elite D9 Percussion Massage Gun</li>
            <li>Product link - <a href="https://www.sportneer.com/product/Sportneer-Elite-D9-Percussion-Massage-Gun">here</a></li>
            <li>Compensation - <b>$200</b></li>
            <li>Platform - <b>Tiktok</b></li>
            <li>Content needed - 1 well-made short video</li>
            <p><b>Bonus- </b></p>
            <li>Meanwhile, we're looking for a few influencers for a 30-min user interview. We will offer a reward of $20 for each participant. <a href="https://lifo.typeform.com/to/nDkj3dsl">Sign up</a> if you're interested.</li>
            <p>Looking forward to seeing you in Lifo.</p>

        '''
        return self.send_sendgrid_email(
            from_email='notifications@lifocommunity.com',
            from_name='Himo from Lifo',
            to_emails=to_email,
            subject=title,
            html_content=html_content
        )

# email_list = ['7dcadc22a0@s.litmustest.com', '7dcadc22a0@sg3.emailtests.com', '7dcadc22a0@ml.emailtests.com', 
# 'barracuda@barracuda.emailtests.com', 'previews_99@gmx.de', 'litmuscheck01@gmail.com', 
# 'litmuscheck01@yahoo.com', 'litmuscheck02@mail.com', 'litmuscheck02@outlook.com', 'litmuscheck03@emailtests.onmicrosoft.com', 
# 'previews_98@web.de', 'litmuscheck02@mail.ru', 'litmuscheck03@gapps.emailtests.com', 'litmustestprod01@gd-testing.com', 
# 'litmustestprod02@yandex.com', 'litmuscheck002@aol.com']
# emailSender = EmailSender()
# for email in email_list:
#     emailSender.send_bait_email_to_unregistered('lifoinc', email)
# emailSender.send_raffle_to_registered('lifoinc', 'shuo.shan@lifo.ai')
# emailSender.send_raffle_to_unregistered('lifoinc', 'internal-alert@lifo.ai')
# emailSender.send_raffle_to_registered('lifoinc', 'ximo.liu@icloud.com')
# emailSender.send_raffle_to_unregistered('lifoinc', 'ximo.liu@icloud.com')
# emailSender.send_raffle_to_registered('lifoinc', 'ximo.liu@yahoo.com')
# emailSender.send_raffle_to_unregistered('lifoinc', 'ximo.liu@yahoo.com')
# print(emailSender.send_invitation_email('lifoinc', 'ximo.liu@icloud.com'))
# emailSender.send_referral_emails([{'instagram_id':'shanshuo0918', 'email':'shuo.shan@lifo.ai'}], 'https://influencer.lifo.ai', 'Shuo Shan 1', 'shanshuo0918@gmail.com', 'shanshuo0918@gmail.com')
# email = 'shuo.shan@lifo.ai'
# print(emailSender.send_accept_discovery_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM'))
# print(emailSender.send_product_shipped_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', '238u9128978179214', 'UPS', 72))
# print(emailSender.send_product_deliver_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', 72, 20, 24))
# print(emailSender.send_draft_approve_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', 10, 'instagram'))
# print(emailSender.send_content_remainder_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', 1604302795, 0))
# print(emailSender.send_post_reminder_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', 1604302795, 0))
# print(emailSender.send_content_overdue_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', 1603945770))
# print(emailSender.send_post_overdue_email(email, 'lifoinc', 'Soft Winter Jacket', 'w72Gl4w8NeOlS8is7XMM', 0))
# print(emailSender.send_commission_issued_email(email, 'lifoinc', 'Soft Winter Jacket', 80))
# print(emailSender.send_payment_complete_email(email, 'lifoinc', 320))