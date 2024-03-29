import unittest
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.core.paginator import Paginator
from ..views import search, get_recipes
from ..forms import ReviewForm
from ..models import Review, Comment, Ingredient, Utensil, Comment, User
from django.contrib.messages import get_messages
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Count


class HomepageTest(TestCase):
    def test_homepage_rendering(self):
        url = reverse('home')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')


class AboutTest(TestCase):
    def test_about_rendering(self):
        url = reverse('about')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about.html')


class TestSearchView(TestCase):
    def setUp(self):
        self.ingredient = Ingredient.objects.create(name='Flour')
        self.utensil = Utensil.objects.create(name='Whisk')
        self.user = User.objects.create_user(username='Alix', password='Bread')
        self.review = Review.objects.create(
            title='Best Bread',
            recipe='Sourdough Bread',
            author=self.user, status=1,
            slug='Best-Bread')

    def test_search_view_with_results(self):
        response = self.client.get(reverse('search'), {'query': 'Flour'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search.html')
        self.assertContains(response, 'Flour')

    def test_search_view_without_results(self):
        response = self.client.gt(
            reverse('search'),
            {'query': 'Rare Ingredient'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search.html')
        self.assertContains(response, 'Rare Ingredient')

    def test_search_view_no_query(self):
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search.html')
        self.assertContains(response, '')


class SearchViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_search_view_post(self):
        request = self.factory.post('/search', {'query': 'search'})

        with patch('pp4app.views.get_recipes') as mock_get_recipes:
            mock_get_recipes.return_value = [
                {'recipe_name': 'Croque Madame'},
                {'recipe_name': 'Pasta Alla Norma'}]
            response = search(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2>Search results for: search</h2>')

        mock_get_recipes.assert_called_once_with('search')

    def test_search_view_get(self):
        request = self.factory.get('/search/', {'query': 'search'})

        with patch('pp4app.views.get_recipes') as mock_get_recipes:
            mock_get_recipes.return_value = [
                {'recipe_name': 'Croque Madame'},
                {'recipe_name': 'Pasta Alla Norma'}]

            response = search(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2>Search results for: search</h2>')
        mock_get_recipes.assert_called_once_with('search')


class GetRecipesTest(unittest.TestCase):
    @patch('pp4app.views.requests.get')
    def test_get_recipes_success(self, mock_requests_get):
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'hits': [
            {'recipe_name': 'Kung Po Chicken'},
            {'recipe_name': 'Prawn Korma'}]}

        mock_requests_get.return_value = mock_response

        result = get_recipes('your_query')

        self.assertEqual(result, [
            {'recipe_name': 'Kung Po Chicken'},
            {'recipe_name': 'Prawn Korma'}])

        mock_requests_get.assert_called_once_with(
            'https://api.edamam.com/api/recipes/v2',
            params={'q': 'your_query',
                    'app_id': unittest.mock.ANY,
                    'app_key': unittest.mock.ANY,
                    'type': 'public'}
                )

    @patch('pp4app.views.requests.get')
    def test_get_recipes_failure(self, mock_requests_get):
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 500

        mock_requests_get.return_value = mock_response

        result = get_recipes('your_query')

        self.assertEqual(result, [])

        mock_requests_get.assert_called_once_with(
            'https://api.edamam.com/api/recipes/v2',
            params={'q': 'your_query',
                    'app_id': unittest.mock.ANY,
                    'app_key': unittest.mock.ANY,
                    'type': 'public'}
                )


if __name__ == '__main__':
    unittest.main()


class ReviewsViewTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='Alix', password='Bread')

        for i in range(7):
            review_title = f'Test Review {i}'
            unique_identifier = f'test-{i}'
            review_slug = slugify(f'{review_title} {unique_identifier}')

            Review.objects.create(
                title=review_title,
                author=self.user,
                created_on=timezone.now() - timezone.timedelta(days=i),
                status=1,
                slug=review_slug
            )

    def test_reviews_view_default_sort(self):
        url = reverse('review_blog')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'review_blog.html')

        expected_reviews =
        Review.objects.filter(status=1).order_by('-created_on')
        self.assertQuerysetEqual(
            response.context['review_list'],
            expected_reviews,
            transform=lambda x: x)

        self.assertTrue('paginator' in response.context)
        paginator = response.context['paginator']
        self.assertTrue(isinstance(paginator, Paginator))
        self.assertEqual(paginator.count, 7)

    def test_reviews_view_custom_sort(self):
        url = reverse('review_blog')
        custom_sort_url = f'{url}?sort=total_votes'
        response = self.client.get(custom_sort_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'review_blog.html')

        expected_reviews = Review.objects.filter(status=1).annotate(
            net_votes_count=Count('up_vote') - Count('down_vote')
        ).order_by('-net_votes_count', '-created_on')
        self.assertQuerysetEqual(
            response.context['review_list'],
            expected_reviews,
            transform=lambda x: x)

    def test_reviews_view_context_data(self):
        url = reverse('review_blog')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTrue('current_sort' in response.context)
        self.assertEqual(response.context['current_sort'], '')


if __name__ == '__main__':
    unittest.main()


class ReviewPostViewTestContext(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='Peter',
            password='sweden')

        self.review = Review.objects.create(
            title='Meatballs',
            author=self.user,
            recipe='swedish_meatballs',
            slug='Meatballs'
        )

        Comment.objects.create(
            review=self.review,
            body='Delicious',
            approved=True,
            created_on=timezone.now() - timezone.timedelta(days=1)
        )
        Comment.objects.create(
            review=self.review,
            body='Ikea Better',
            approved=True,
            created_on=timezone.now() - timezone.timedelta(days=2)
        )

    def test_get_context_data(self):
        self.client.login(username='Veronica', password='liberty')

        url = f'/review/{self.review.slug}/'

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)


class ReviewPostViewTestPost(TestCase):
    def setUp(self):

        self.user = User.objects.create_user(
            username='ChristopherFrancisDerekRyan',
            password='password123')

        title = 'Nice for dinner'
        slug = slugify(title)

        self.review = Review.objects.create(
            title='Nice for dinner',
            recipe='Soup',
            author=self.user,
            created_on=timezone.now(),
            status=1,
            slug=slug
        )

        self.client.login(
                username='ChristopherFrancisDerekRyan',
                password='password123')

        self.comment_form_data = {
            'body': 'This is a test comment.',

        }

    def test_post_method(self):
        url = reverse('review_post', kwargs={'slug': self.review.slug})

        response = self.client.post(url, data=self.comment_form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Awaiting approval')

        comment = Comment.objects.get(
            review=self.review,
            body='This is a test comment.')
        comment.approved = True
        comment.save()

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'This is a test comment.')


class ReviewUpvoteViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='ChrisR',
            password='password123')

        self.review = Review.objects.create(
            title='Fish and Chips',
            author=self.user,
            created_on=timezone.now(),
            status=1,
            slug="Fish_and_Chips"
        )

        self.client.login(username='ChrisR', password='password123')

    def test_upvote_post(self):
        url = reverse('review_upvote', args=[self.review.slug])

        response = self.client.post(url, {'vote_type': 'upvote'})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('review_post', args=[self.review.slug]))

        self.assertTrue(self.review.up_vote.filter(id=self.user.id).exists())

        self.assertFalse(
            self.review.down_vote.filter(id=self.user.id).exists())

    def test_downvote_post(self):
        url = reverse('review_upvote', args=[self.review.slug])

        response = self.client.post(url, {'vote_type': 'downvote'})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse(
            'review_post',
            args=[self.review.slug]))

        self.assertTrue(self.review.down_vote.filter(id=self.user.id).exists())
        self.assertFalse(self.review.up_vote.filter(id=self.user.id).exists())


class UpdateReviewViewTestGet(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='TrickyDicky',
            password='nixon')

        self.review = Review.objects.create(
            title='Nice for dinner',
            author=self.user,
            created_on=timezone.now(),
            status=1,
            slug='Nice_for_dinner'
        )

        self.client.login(username='TrickyDicky', password='nixon')

    def test_get_method(self):
        url = reverse('update_review', kwargs={'slug': self.review.slug})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, 'update_review.html')

        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], ReviewForm)

        self.assertIn('review', response.context)
        self.assertEqual(response.context['review'], self.review)


class UpdateReviewTestCasePost(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='RichardFanning',
            password='kilkenny')

        self.review = Review.objects.create(
            title='Stew',
            recipe='Irish Stew',
            content='Quality Stew',
            author=self.user,
            slug='Stew'
        )

    def test_post_delete_review(self):
        self.client.login(username='RichardFanning', password='kilkenny')

        url = reverse('update_review', args=[self.review.slug])

        response = self.client.post(url, {'delete': ''})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_update_review_successful(self):

        self.client.login(username='RichardFanning', password='kilkenny')

        url = reverse('update_review', args=[self.review.slug])

        form_data = {
            'title': 'Updated Test Review',
            'recipe': 'Old Recipe',
            'content': 'Updated content for the review',
            'slug': 'new-test-slug'
        }

        response = self.client.post(url, form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        updated_review = Review.objects.get(id=self.review.id)
        self.assertEqual(updated_review.title, 'Updated Test Review')
        self.assertEqual(
            updated_review.content,
            'Updated content for the review')

    def test_update_review_invalid_form(self):
        review = Review.objects.create(
            title='Test Review1',
            content='This is a test review.',
            author=self.user,
            slug='test-review-1'
        )

        self.client.login(username='RichardFanning', password='kilkenny')

        url = reverse('update_review', args=[review.slug])

        invalid_form_data = {
            'title': '',
            'content': 'Updated content for the review',
            'ingredients': [1, 2],
            'new_ingredient': 'New Ingredient 1, New Ingredient 2',
        }

        response = self.client.post(url, invalid_form_data)

        self.assertEqual(response.status_code, 200)
        updated_review = Review.objects.get(id=review.id)
        self.assertNotEqual(updated_review.title, '')


class DeleteCommentViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        self.review = Review.objects.create(
            title='Test Review',
            content='This is a test review',
            author=self.user,
            slug=slugify('Test Review')
        )

        self.comment = Comment.objects.create(
            review=self.review,
            name='testuser',
            body='This is a test comment'
        )

        self.client = Client()

    def test_delete_comment_success(self):
        self.client.login(username='testuser', password='testpassword')

        url = reverse('delete_comment', kwargs={'comment_id': self.comment.id})

        response = self.client.post(url)

        self.assertEqual(Comment.objects.filter(
            id=self.comment.id).exists(),
            False)

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn('Comment deleted successfully', messages)

        self.assertRedirects(
            response,
            reverse('review_post',
                    kwargs={'slug': self.review.slug}))

    def test_delete_comment_permission_denied(self):
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpassword'
        )

        self.client.login(username='otheruser', password='otherpassword')
        url = reverse('delete_comment', kwargs={'comment_id': self.comment.id})
        response = self.client.post(url)
        self.assertEqual(
            Comment.objects.filter(id=self.comment.id).exists(), True)

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn(
            'You do not have permission to delete this comment',
            messages)
        self.assertRedirects(response, reverse(
            'review_post',
            kwargs={'slug': self.review.slug}))


class CustomSignupViewTest(TestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        }

        self.client = Client()

    def test_signup_view_get(self):
        url = reverse('account_signup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/signup.html')

    def test_signup_view_post_success(self):
        url = reverse('account_signup')
        response = self.client.post(url, data=self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

        self.assertTrue(User.objects.filter(
            username=self.user_data['username']).exists())

    def test_signup_view_post_failure(self):
        self.user_data['password2'] = 'DifferentPassword123!'

        url = reverse('account_signup')
        response = self.client.post(url, data=self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/signup.html')

        self.assertFalse(User.objects.filter(
            username=self.user_data['username']).exists())


class CustomLoginViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPassword123!'
        )

        self.client = Client()

    def test_login_view_get(self):
        url = reverse('account_login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/login.html')

    def test_login_view_post_success(self):
        url = reverse('account_login')
        login_data = {
            'login': self.user.username,
            'password': 'TestPassword123!'
        }
        response = self.client.post(url, data=login_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/login.html')

    def test_login_view_post_failure(self):
        url = reverse('account_login')
        login_data = {
            'login': self.user.username,
            'password': 'IncorrectPassword123!'
        }
        response = self.client.post(url, data=login_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/login.html')


class ErrorViewsTest(TestCase):
    def test_bad_request_view(self):
        response = self.client.get('/400/')
        self.assertEqual(response.status_code, 400)

    def test_permission_denied_view(self):
        response = self.client.get('/403/')
        self.assertEqual(response.status_code, 403)

    def test_page_not_found_view(self):
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)

    def test_server_error_view(self):
        response = self.client.get('/500/')
        self.assertEqual(response.status_code, 500)
