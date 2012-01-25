r"""
    facebook_utils
    ~~~~~~~~~~~~

    A collection of utilities for integrating user accoutns with Facebook.com
    
    right now this handles oauth , but will likely expand
    
    Purpose
    =======
    
    1. Facebook dropped development and support of their python sdk
    
    2. There are a handful of pyramid utilities that provide a complete drop-in 
    integration with Facebook.com; This is NOT one of them. Sometimes you want 
    to control the User Experience and have all your pages custom; if so, this
    is for you.
        
    
    Usage
    =====
    
    This was originally built/intended for use under the Pyramid environment
    
    calling FacebookPyramid() will create a new object that 
    proxies FacebookHub() objects, using  default settings 
    from your .ini and pulling variables from 'request' as needed.
    
    facebook_utils.FacebookHub() can be used directly - however it will not 
    pull settings from the .ini or request.
    
    
    Supports Two oAuth Flows
    =========================
    
    Flow 1 - Server Side
    --------------------
    1. configure an object with `oauth_code_redirect_uri`
    2. consumers click a button on your site, which redirects to 
    `oauth_code_redirect_uri` -- as provided by `oauth_code__url_dialog()`
    3. upon success, users are redirected from facebook to 
    `oauth_code_redirect_uri` along with a query param titled `code`
    4. you may then call `.oauth_code__get_access_token()` to get an access 
    token or call `oauth_code__get_access_token_and_profile()` to get the token 
    and profile data.
    5. profile data can be updated with `.graph__get_profile(access_token)`
    
    
    Flow 2 - Client Side
    --------------------
    1. configure an object with `oauth_token_redirect_uri`
    2. consumers click a button on your site, which redirects to 
    `oauth_token_redirect_uri` -- as provided by `oauth_token__url_dialog()`
    3. upon success, users are redirected from facebook to 
    `oauth_token__url_dialog` along with a query param titled `token` and a 
    hash value titled `#access_token`.  The `access_token` is not visible to
    the server, and must be transferred to your server via JavaScript or 
    not-at-all should you simply want to do all your integration in JavaScript.
    4. profile data can be obtained with `.graph__get_profile(access_token)`
    if you store the access token
    
    
    Notes
    =====
    Most methods will let you override the 'scope' and 'request_uri'.  This 
    shouldn't really be necessary and will probable be deprecated.
    
    
    
    
    
    Pyramid Examples
    ================
    define some variables in your .ini files:
    
    file: development.ini

        facebook.app.id= 123
        facebook.app.secret= 123
        facebook.app.scope= email,user_birthday,user_checkins,offline_access
        
    
    integrate into your handlers:
        
        from facebook_utils import FacebookPyramid
    
        class WebAccount(base.Handler):
            def __new_fb_object(self):
                "Create a new Facebook Object"
                oauth_code_redirect_uri= "http://%(app_domain)s/account/facebook-authenticate-oauth?response_type=code" % { 'app_domain' : self.request.registry.settings['app_domain']}
                oauth_token_redirect_uri= "http://%(app_domain)s/account/facebook-authenticate-oauth-token?response_type=token" % { 'app_domain' : self.request.registry.settings['app_domain']}
                fb= FacebookPyramid( self.request , oauth_code_redirect_uri=oauth_code_redirect_uri )
                return fb
    
            def sign_up(self):
                "sign up page, which contains a "signup with facebook link"
                fb= self.__new_fb_object()
                return {"project":"MyApp" , 'facebook_pyramid':facebook }
    
            @action(renderer="web/account/facebook_authenticate_oauth.html")
            def facebook_authenticate_oauth(self):
                fb= self.__new_fb_object()
                ( access_token , profile )= fb.oauth_code__get_access_token_and_profile( self.request )
                if profile :
                    # congrats , they logged in
                    # register the user to your db 
                    raise HTTPFound(location='/account/home')
                else:
                    # boo, that didn't work
                    raise HTTPFound(location='/account/sign-up?error=facebook-oauth-failure')
                return {"project":"MyApp"}


    integrate into your template:
                <a class="fancy_button-1" id="signup-start_btn-facebook" href="${facebook_pyramid.oauth_code__url_dialog()}">
                    Connect with <strong>Facebook</strong>
                </a>
    

    :copyright: 2012 by Jonathan Vanasco
    license: BSD
"""

import urllib
import urllib2
import simplejson as json
import cgi



class FacebookHub(object):

    app_id= None
    app_secret= None
    app_scope= None
    app_domain= None
    oauth_code_redirect_uri= None
    oauth_token_redirect_uri= None
    
    def __init__( self, app_id=None , app_secret=None , app_scope=None , app_domain=None , oauth_code_redirect_uri=None , oauth_token_redirect_uri=None ):
        self.app_id= app_id
        self.app_secret= app_secret
        self.app_scope= app_scope
        self.app_domain= app_domain
        self.oauth_code_redirect_uri = oauth_code_redirect_uri
        self.oauth_token_redirect_uri= oauth_token_redirect_uri


    def oauth_code__url_dialog( self, redirect_uri=None , scope=None ):
        """Generates the URL for an oAuth dialog to facebook.  This flow will return the user to your website with a 'code' object in a query param. """
        if scope == None:
            scope= self.app_scope
        if redirect_uri == None:
            redirect_uri= self.oauth_code_redirect_uri
        return """https://www.facebook.com/dialog/oauth?client_id=%(app_id)s&scope=%(scope)s&redirect_uri=%(redirect_uri)s""" % { 'app_id':self.app_id, "redirect_uri":urllib.quote( redirect_uri ) , 'scope':scope }
        

    def oauth_code__url_access_token( self, submitted_code=None , redirect_uri=None , scope=None ):
        """Generates the URL for an oAuth dialog
        https://graph.facebook.com/oauth/access_token?client_id=YOUR_APP_ID&redirect_uri=YOUR_URL&client_secret=YOUR_APP_SECRET&code=THE_CODE_FROM_URL_DIALOG_TOKEN 
        
        """
        if redirect_uri == None:
            redirect_uri= self.oauth_code_redirect_uri
        if scope == None:
            scope= self.app_scope
        if submitted_code == None:
            raise ValueError('missing submitted code')
        return """https://graph.facebook.com/oauth/access_token?client_id=%(app_id)s&redirect_uri=%(redirect_uri)s&client_secret=%(client_secret)s&code=%(code)s""" % { 'app_id':self.app_id , "redirect_uri":urllib.quote( redirect_uri ) , 'client_secret':self.app_secret, 'code':submitted_code }
            

    def oauth_code__get_access_token( self , submitted_code=None , redirect_uri=None , scope=None ):
        """Gets the access token from facebook"""
        if scope == None:
            scope= self.app_scope
        if redirect_uri == None:
            redirect_uri= self.oauth_code_redirect_uri
        if submitted_code == None:
            raise ValueError('missing submitted code')
        url_access_token = self.oauth_code__url_access_token( submitted_code , redirect_uri=redirect_uri , scope=scope )
        access_token = None
        try:
            response = cgi.parse_qs(urllib.urlopen(url_access_token).read())
            if 'access_token' not in response:
                raise ValueError('invalid response')
            access_token = response["access_token"][-1]
        except:
            raise
        return access_token       
        
        
    def oauth_code__get_access_token_and_profile( self , submitted_code=None , redirect_uri=None , scope=None  ):
        if submitted_code == None:
            raise ValueError('missing submitted code')
        url_access_token = self.oauth_code__url_access_token( submitted_code , redirect_uri=redirect_uri , scope=scope )
        ( access_token , profile ) = ( None , None )
        try:
            response = cgi.parse_qs(urllib.urlopen(url_access_token).read())
            if 'access_token' not in response:
                raise ValueError('invalid response')
            access_token = response["access_token"][-1]
            profile = json.load(urllib.urlopen( self.graph__url_me(access_token) ))
        except:
            raise
        return ( access_token , profile )        


    def oauth_token__url_dialog( self, redirect_uri=None , scope=None ):
        """Generates the URL for an oAuth dialog to facebook.  This flow will return the user to your website with a 'token' object as a URI hashstring.  This hashstring can not be seen by the server, it must be handled via javascript """
        if scope == None:
            scope= self.app_scope
        if redirect_uri == None:
            redirect_uri= self.oauth_token_redirect_uri
        return """https://www.facebook.com/dialog/oauth?client_id=%(app_id)s&scope=%(scope)s&redirect_uri=%(redirect_uri)s&response_type=token""" % { 'app_id':self.app_id , "redirect_uri":urllib.quote( redirect_uri ) , 'scope':scope }
        



    def graph__url_me( self , access_token ):
        return "https://graph.facebook.com/me?" + urllib.urlencode(dict(access_token=access_token))
    

    def graph__get_profile( self , access_token=None  ):
        profile= None
        try:
            profile = json.load(urllib.urlopen( self.graph__url_me(access_token) ))
        except:
            raise
        return profile       
    


class FacebookPyramid(object):

    def __init__( self, request , app_id=None , app_secret=None , app_scope=None , app_domain=None , oauth_code_redirect_uri=None , oauth_token_redirect_uri=None ):
        """Creates a new FacebookHub object, sets it up with Pyramid Config vars, and then proxies other functions into it"""
        self.request= request
        if app_id is None:
            app_id = request.registry.settings['facebook.app.id']
        if app_secret is None:
            app_secret = request.registry.settings['facebook.app.secret']
        if app_scope is None and 'facebook.app.scope' in request.registry.settings :
            app_scope = request.registry.settings['facebook.app.scope']
        if app_domain is None:
            app_domain = request.registry.settings['app_domain']
        self.facebookHub= FacebookHub( app_id=app_id , app_secret=app_secret , app_scope=app_scope , app_domain=app_domain , oauth_code_redirect_uri=oauth_code_redirect_uri , oauth_token_redirect_uri=oauth_token_redirect_uri )
        

    def oauth_code__url_dialog( self , redirect_uri=None , scope=None ):
        return self.facebookHub.oauth_code__url_dialog( redirect_uri=redirect_uri , scope=scope )

    def oauth_code__url_access_token( self, submitted_code=None , redirect_uri=None , scope=None ):
        if submitted_code is None:
            submitted_code = self.request.params.get('code')
        return self.facebookHub.oauth_code__url_access_token( submitted_code=submitted_code , redirect_uri=redirect_uri , scope=scope )

    def oauth_code__get_access_token( self , submitted_code=None , redirect_uri=None , scope=None ):
        if submitted_code is None:
            submitted_code = self.request.params.get('code')
        return self.facebookHub.oauth_code__get_access_token( submitted_code=submitted_code , redirect_uri=redirect_uri , scope=scope )

    def oauth_code__get_access_token_and_profile( self , submitted_code=None , redirect_uri=None , scope=None ):
        if submitted_code is None:
            submitted_code = self.request.params.get('code')
        return self.facebookHub.oauth_code__get_access_token_and_profile( submitted_code=submitted_code , redirect_uri=redirect_uri , scope=scope )


    def oauth_token__url_dialog( self , redirect_uri=None , scope=None ):
        return self.facebookHub.oauth_token__url_dialog( redirect_uri=redirect_uri , scope=scope )


    def graph__url_me( self , access_token ):
        return self.facebookHub.graph__url_me( access_token )

    def graph__get_profile( self , access_token ):
        return self.facebookHub.graph__get_profile( access_token )
