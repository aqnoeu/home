import unittest
from home_emotions import ContextState, normalize_emotion

class EmotionTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(normalize_emotion("raiva"), "raiva")
        self.assertEqual(normalize_emotion("sonolento"), "sonolento")
        self.assertEqual(normalize_emotion("tdio"), "neutro")
    def test_priority(self):
        state=ContextState(last_activity=1.,focused_window=7,focused_since=1.)
        state.note_conversation("raiva", now=1000.)
        self.assertEqual(state.choose(1003.,charging=True),"raiva")
        self.assertEqual(state.choose(1100.,charging=True),"carregando")
        self.assertEqual(state.choose(1401.,charging=False),"sonolento")
    def test_operational_statuses_without_intrusive_notifications(self):
        state=ContextState(last_activity=990.,focused_since=990.)
        self.assertEqual(state.choose(1000.,battery_low=True),"bateria_baixa")
        self.assertEqual(state.choose(1000.,power_saver=True),"economia")
        self.assertEqual(state.choose(1000.,charging=True,battery_low=True),"carregando")

    def test_boredom_without_idle(self):
        state=ContextState(last_activity=999.,focused_window=7,focused_since=100.)
        self.assertEqual(state.choose(1000.,charging=False),"tedio")

if __name__=="__main__":
    unittest.main()
