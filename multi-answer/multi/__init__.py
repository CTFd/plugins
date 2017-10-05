from CTFd.plugins.keys import get_key_class
from CTFd.plugins import challenges
from CTFd.plugins import keys
from CTFd.plugins.keys import BaseKey
from flask import request, redirect, jsonify, url_for, session, abort
from CTFd.models import db, Challenges, WrongKeys, Keys, Teams, Awards
from CTFd import utils
import logging
import time
from CTFd.plugins.challenges import get_chal_class

class MultiChallenge(challenges.BaseChallenge):
    """Multi-Challenge allows right and wrong answers and leaves the question open"""
    id = 2
    name = "multi-challenge"

    def attempt(chal, request):
        """Attempt the user answer to see if it's right"""
        provided_key = request.form['key'].strip()
        chal_keys = Keys.query.filter_by(chal=chal.id).all()
        for chal_key in chal_keys:
            if get_key_class(chal_key.key_type).compare(chal_key.flag, provided_key):
                if chal_key.key_type == 0:
                    return True, 'Correct'
                elif chal_key.key_type == 2:
                    return False, 'Failed Attempt'
        return False, 'Incorrect'

    @staticmethod
    def solve(team, chal, request):
        """Solve the question and put results in the Awards DB"""
        provided_key = request.form['key'].strip()
        solve = Awards(teamid=team.id, name=chal.id, value=chal.value)
        solve.description = provided_key
        db.session.add(solve)
        db.session.commit()
        db.session.close()

    @staticmethod
    def fail(team, chal, request):
        """Standard fail if the question is wrong record it"""
        provided_key = request.form['key'].strip()
        wrong = WrongKeys(teamid=team.id, chalid=chal.id, ip=utils.get_ip(request), flag=provided_key)
        db.session.add(wrong)
        db.session.commit()
        db.session.close()

    def wrong(team, chal, request):
        """Fail if the question is wrong record it and record the wrong answer to deduct points"""
        provided_key = request.form['key'].strip()
        wrong_value = 0
        wrong_value -= chal.value
        wrong = WrongKeys(teamid=team.id, chalid=chal.id, ip=utils.get_ip(request), flag=provided_key)
        solve = Awards(teamid=team.id, name=chal.id, value=wrong_value)
        solve.description = provided_key
        db.session.add(wrong)
        db.session.add(solve)
        db.session.commit()
        db.session.close()


class CTFdWrongKey(BaseKey):
    """Wrong key to deduct points from the player"""
    id = 2
    name = "Wrong"

    @staticmethod
    def compare(saved, provided):
        """Compare the saved and provided keys"""
        if len(saved) != len(provided):
            return False
        result = 0
        for x, y in zip(saved, provided):
            result |= ord(x) ^ ord(y)
        return result == 0


def chal(chalid):
    """Custom chal function to override challenges.chal when multi-answer is used"""
    if utils.ctf_ended() and not utils.view_after_ctf():
        abort(403)
    if not utils.user_can_view_challenges():
        return redirect(url_for('auth.login', next=request.path))
    if (utils.authed() and utils.is_verified() and (utils.ctf_started() or utils.view_after_ctf())) or utils.is_admin():
        team = Teams.query.filter_by(id=session['id']).first()
        fails = WrongKeys.query.filter_by(teamid=session['id'], chalid=chalid).count()
        logger = logging.getLogger('keys')
        data = (time.strftime("%m/%d/%Y %X"), session['username'].encode('utf-8'), request.form['key'].encode('utf-8'), utils.get_kpm(session['id']))
        print("[{0}] {1} submitted {2} with kpm {3}".format(*data))

        # Anti-bruteforce / submitting keys too quickly
        if utils.get_kpm(session['id']) > 10:
            if utils.ctftime():
                wrong = WrongKeys(teamid=session['id'], chalid=chalid, ip=utils.get_ip(), flag=request.form['key'].strip())
                db.session.add(wrong)
                db.session.commit()
                db.session.close()
            logger.warn("[{0}] {1} submitted {2} with kpm {3} [TOO FAST]".format(*data))
            # return '3' # Submitting too fast
            return jsonify({'status': 3, 'message': "You're submitting keys too fast. Slow down."})

        solves = Awards.query.filter_by(teamid=session['id'], name=chalid, description=request.form['key'].strip()).first()

        # Challenge not solved yet
        try:
            flag_value = solves.description
        except AttributeError:
            flag_value = ""
        if request.form['key'].strip() != flag_value or not solves:
            chal = Challenges.query.filter_by(id=chalid).first_or_404()
            provided_key = request.form['key'].strip()
            saved_keys = Keys.query.filter_by(chal=chal.id).all()

            # Hit max attempts
            max_tries = chal.max_attempts
            if max_tries and fails >= max_tries > 0:
                return jsonify({
                    'status': 0,
                    'message': "You have 0 tries remaining"
                })

            chal_class = get_chal_class(chal.type)
            status, message = chal_class.attempt(chal, request)
            if status:  # The challenge plugin says the input is right
                if utils.ctftime() or utils.is_admin():
                    chal_class.solve(team=team, chal=chal, request=request)
                logger.info("[{0}] {1} submitted {2} with kpm {3} [CORRECT]".format(*data))
                return jsonify({'status': 1, 'message': message})
            elif message == "Failed Attempt":
                if utils.ctftime() or utils.is_admin():
                    chal_class.wrong(team=team, chal=chal, request=request)
                logger.info("[{0}] {1} submitted {2} with kpm {3} [Failed Attempt]".format(*data))
                return jsonify({'status': 1, 'message': message})
            else:  # The challenge plugin says the input is wrong
                if utils.ctftime() or utils.is_admin():
                    chal_class.fail(team=team, chal=chal, request=request)
                logger.info("[{0}] {1} submitted {2} with kpm {3} [WRONG]".format(*data))
                # return '0' # key was wrong
                if max_tries:
                    attempts_left = max_tries - fails - 1  # Off by one since fails has changed since it was gotten
                    tries_str = 'tries'
                    if attempts_left == 1:
                        tries_str = 'try'
                    if message[-1] not in '!().;?[]\{\}':  # Add a punctuation mark if there isn't one
                        message = message + '.'
                    return jsonify({'status': 0, 'message': '{} You have {} {} remaining.'.format(message, attempts_left, tries_str)})
                else:
                    return jsonify({'status': 0, 'message': message})

        # Challenge already solved
        else:
            logger.info("{0} submitted {1} with kpm {2} [ALREADY SOLVED]".format(*data))
            # return '2' # challenge was already solved
            return jsonify({'status': 2, 'message': 'You already solved this'})
    else:
        return jsonify({
            'status': -1,
            'message': "You must be logged in to solve a challenge"
        })


def open_multihtml():
    with open('CTFd/plugins/multi/assets/multiteam.html') as multiteam:
        multiteam_string = str(multiteam.read())
    multiteam.close()
    return multiteam_string


def load(app):
    """load overrides for multi-answer plugin to work properly"""
    utils.override_template('team.html', open_multihtml())
    challenges.CHALLENGE_CLASSES[2] = MultiChallenge
    keys.KEY_CLASSES[2] = CTFdWrongKey
    app.view_functions['challenges.chal'] = chal

