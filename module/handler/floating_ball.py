from module.base.timer import Timer
from module.handler.assets import (FLOAT_BALL_360, FLOAT_BALL_360_CLOSE,
                                   FLOAT_BALL_360_HIDE)
from module.handler.info_handler import InfoHandler
from module.logger import logger


class FloatingBallHandler(InfoHandler):
    """
    Handle the assistant floating ball of the 360 (qihoo) game client.

    The 360 client draws its own assistant floating ball above the game. The ball is
    docked at the left edge of the screen, only its right half is visible, and it is
    recreated on every game start. Instead of masking it out during recognition, the
    ball is hidden right after login by the ball's own "隐藏浮球" option.
    """

    def _float_ball_appear(self):
        """
        Returns:
            bool: If the floating ball appears on the screen.
        """
        # An integer offset makes Button.match() search vertically only, because the
        # ball is docked at the left edge of the screen but can be dragged up and down.
        # Similarity 0.9 has a large margin: the asset matches 1.000 with the badge
        # digit and 1.000 with the digit gone, 0.980 over a different background.
        return self.appear(FLOAT_BALL_360, offset=60, similarity=0.9)

    def handle_floating_ball(self):
        """
        Pages:
            in: page_main
            out: page_main

        Returns:
            bool: If handled.
        """
        # The ball is created by the 360 SDK when the game starts, it may be a bit later
        # than the moment we reached page_main.
        appear_timer = Timer(3).start()
        while 1:
            self.device.screenshot()
            if self._float_ball_appear():
                break
            if appear_timer.reached():
                logger.info('360 floating ball not found')
                return False

        # Click the ball to open the 360 assistant panel, click "隐藏浮球", then leave
        # the panel. The panel covers the whole screen, is not a game page, and would
        # break every recognition if it was left open.
        logger.hr('360 floating ball', level=2)
        hide_clicked = False
        timeout = Timer(20).start()
        while 1:
            self.device.screenshot()

            # End
            if not self.appear(FLOAT_BALL_360_HIDE, offset=(30, 30)) \
                    and not self._float_ball_appear() \
                    and self.is_in_main():
                logger.info('360 floating ball hidden')
                return True
            if timeout.reached():
                logger.warning('Failed to hide the 360 floating ball')
                break

            # Click
            if self.appear(FLOAT_BALL_360_HIDE, offset=(30, 30)):
                if not hide_clicked:
                    if self.appear_then_click(FLOAT_BALL_360_HIDE, offset=(30, 30), interval=2):
                        hide_clicked = True
                        continue
                # The panel is still there after clicking hide, leave it
                if self.appear_then_click(FLOAT_BALL_360_CLOSE, offset=(30, 30), interval=2):
                    hide_clicked = False
                    continue
            else:
                if self.appear_then_click(FLOAT_BALL_360, offset=60, similarity=0.9, interval=3):
                    continue

        # Failed, but never leave the assistant panel open
        if self.appear(FLOAT_BALL_360_HIDE, offset=(30, 30)):
            self.device.click(FLOAT_BALL_360_CLOSE)
            self.device.screenshot()
        if not self.is_in_main():
            self.ui_goto_main()
        return False
