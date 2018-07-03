<template>
    <div id="google_button" ref="google_button" class="g-signin2"></div>
</template>

<script>
    export default {
        name: "google-login",
        props: ['client_id']
        ,
        created() {
            // according to the internet https://www.google.co.il/search?q=vuejs+add+script+tag
            // the best way to add a script tag to a page in vue is by using this:
            let meta = document.createElement('meta')
            meta.setAttribute('name', 'google-signin-client_id')
            meta.setAttribute('content', this.client_id)
            document.head.appendChild(meta)

            let script = document.createElement('script')
            script.setAttribute('src', "https://apis.google.com/js/platform.js")
            script.setAttribute('async', '')
            script.setAttribute('defer', '')
            document.head.appendChild(script)
            let self = this
            script.addEventListener("load", () => {
                console.log("On load")
                window.gapi.load('auth2', () => {
                    const auth2 = window.gapi.auth2.getAuthInstance()
                    if (auth2.isSignedIn.get())
                    {
                        // this happens if:
                        // a. user logged out of axonius and for some reason log out of google failed;
                        // b. user logged in an unauthorized account and refreshed the page;
                        auth2.signOut()
                    }
                    auth2.attachClickHandler(self.$refs.google_button.id, {}, googleUser => {
                        self.$emit('success', googleUser)
                    }, error => {
                        self.$emit('error', error)
                    })
                })
            })
        }
    }
</script>

<style scoped>

</style>