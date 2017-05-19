#!usr/bin/env python

import sys
import difflib

def load_dictionary(in_file, nsubs):
   words = {}
   fd = open(in_file)
   for l in fd:
      for w in l.rstrip().split():
         w_data = [None] * (nsubs + 1)
         w_data[0] = True
         words[w] = w_data
   fd.close()
   return words

class Distance2:
   def __init__(self, w, ww):
      sm = difflib.SequenceMatcher(None, ww, w)
      self.__value = sm.ratio()

   def compute(self):
      return self.__value

class LevenshteinDistance:
   def __init__(self, w, ww):
      self.__value = 0
      lw = len(w)
      lw1 = lw + 1
      lww = len(ww)
      lww1 = lww + 1

      d = [[0] * lww1] * lw1
      
      for i in xrange(1, lw1): 
         d[i][0] = i

      for j in xrange(1, lww1): 
         d[0][j] = j

      for j in xrange(1, lww):
         for i in xrange(1, lw):
            if ww[j] == w[i]:
               subcost = 0
            else:
               subcost = 1
            d[i][j] = 1.0/min([d[i-1][j]  + 1, d[i][j-1] + 1, d[i-1][j-1] + subcost])

      self.__value = d[lw][lww]

   def compute(self):
      return self.__value


class Distance:
   def __init__(self, w, ww):
      self.__value = 0.
      self.__value = (self.__one_way_embed(w, ww) + self.__one_way_embed(ww, w))/2.0

   def __one_way_embed(self, w, ww):
      ww_idx = 0
      lww = len(ww)
      matched = 0
      for w_idx, w_char in enumerate(w):
         while ww_idx < lww:
           if ww[ww_idx] == w_char:
             ww_idx += 1
             matched += 1 
             break
           else:
             ww_idx += 1
      non_matched = len(w) - matched
      score = matched*matched - non_matched*non_matched
      return score

   def compute(self):
      return self.__value

class Context:
   def __init__(self, n):
      if n < 1:
         raise Exception("Cannot specify context with negative size")

      self._words = [None] * (2*n + 1)
      self._n = n
      self._sz = (2*n+1)
      self._cur_idx = -1
      self._tot_idx = -1

   def add(self, w, ln, cn):
      self._cur_idx = (self._cur_idx + 1) % self._sz
      self._tot_idx += 1
      self._words[self._cur_idx] = (w, ln, cn)
      #print "Added: words (%s)" % str(self._words)

   def mid_word(self):
      mw_idx = self.mid_word_idx()
      if mw_idx is None:
         return None
      return self._words[mw_idx]

   def mid_word_idx(self):
      mw_idx = self._tot_idx - self._n + 1
      if mw_idx < 0:
         return None
      return (self._cur_idx - self._n) % self._sz

   def as_string(self):
      if self._cur_idx < 0:
         return

      orig_idx = self._cur_idx
      next_idx = (self._cur_idx + 1) % self._sz

      words = self._words

      ctxt = [None] * self._sz
      ctxt_idx = 0

      #print "AS?: %s" % str(self._words)

      for z in xrange(0, self._sz):
         if words[next_idx] is not None:
            ctxt[ctxt_idx] = words[next_idx]
            ctxt_idx += 1
         next_idx = (next_idx + 1) % self._sz

      if ctxt[0] is not None:
         return ' '.join(c[0] for c in ctxt if c is not None)
      else:
         return ''

class SpellChecker:
   def __init__(self, dict_file, n, n_subs):
      self._words = load_dictionary(dict_file, n_subs)
      self._ctxt_size = n
      self._n_subs = n_subs

   def __autoPass(self, w):
      # Check that the words belongs to some category that is
      # automatically considered spelled correctly.
      return self.__isProper(w) or \
             self.__isI(w)

   def __isI(self, w):
      # The word 'I' may be considered a misspelling in the provided dictionary,
      # but I wanted to have another condition to check under the __autoPass function.
      return w == 'I'

   def __isProper(self, w):
      # Determine whether a name is proper;
      # basic pattern is a capital letter followed by all lowercase
      # other patterns may be possible
      return len(w) > 1 and \
             w[0] == w[0].upper() and \
             w[1:] == w[1:].lower()

   def __wordmatchScore(self, w, ww):
      # Compute a score giving the closeness of the match between these words.
      #d = Distance(w, ww)
      #d = LevenshteinDistance(w, ww)
      d = Distance2(w, ww)
      return d.compute()

   def __populateSubs(self, w):
      ns = self._n_subs
      sl = [None] * (ns + 1)
      sl[0] = False
      subs = [None] * ns
      ns1 = ns+1

      min_wms = None

      for ww in self._words.iterkeys():
         w_score = self.__wordmatchScore(w, ww)
         if min_wms is not None and w_score < min_wms and subs[-1] is not None:
            continue

         # Look for an empty slot
         found_empty = False
         for x in xrange(1, ns1):
            if subs[-x] is None:
               subs[-x] = [w_score, ww]
               found_empty = True
               break  

         if found_empty:
            subs.sort()
            min_wms = subs[-1][0]
            continue

         # The word list is full, so we check scores
         # Check the current minimum score
         if subs[-1][0] >= w_score:
            continue


         # Bubble the new entry up
         for x in xrange(1, ns):
            entry = subs[-x]
            prev_entry = subs[-(x+1)]
            if entry[0] > prev_entry[0]:
               # Swap
               tmp_score = entry[0]
               tmp_ww = entry[1]
               entry[0] = prev_entry[0]
               entry[1] = prev_entry[1]
               prev_entry[0] = tmp_score
               prev_entry[1] = tmp_ww
            else:
               break
            
         min_wms = subs[-1][0]

      for zz, entry in enumerate(subs):
         sl[zz+1] = entry[1]

      return sl

   def __isMisspelled(self, w):
      lw = w.lower()
      try:
         subs_list = self._words[lw]
         if not subs_list[0]:
            return subs_list
         else:
            return None
      except KeyError:
         subs_list = self.__populateSubs(w)
         self._words[w] = subs_list
         return subs_list

   def check_word(self, w, ln, cn, ctxt):
      w = w.rstrip('.')
      if self.__autoPass(w):
         return
      sl = self.__isMisspelled(w)
      if sl is None:
         return
      #print "SL is (%s)" % str(sl)
      cc = ctxt.as_string()
      print "Word (%s) is mispelled on line %d column %d...context is  (%s), possible substitutes are (%s)" % (w, ln, cn, cc, ' '.join(subw for subw in sl[1:] if subw is not None))


   def check(self, txt):
      ctxt = Context(self._ctxt_size)
      fd = open(txt)
      line_no = 1
      for l in fd:
         col_n = 0
         col_i = 0
         while col_i < len(l):
            if l[col_i] == ' ':
               col_i += 1
               continue
            break
         words = l[col_i:].rstrip().split(' ')
         for w in words:
            ctxt.add(w, line_no, col_i)
            mw = ctxt.mid_word()
            if mw is not None:
               self.check_word(mw[0], mw[1], mw[2], ctxt)
            col_i += (len(w) + 1)
         line_no += 1

      fd.close()

      # Catch up the context

      while True:
         ctxt.add('', -1, -1);
         mw = ctxt.mid_word()
         if mw[1] < 0:
            break
         self.check_word(mw[0], mw[1], mw[2], ctxt)
         

if __name__ == "__main__":
   dict_file = sys.argv[1]
   text = sys.argv[2]

   sc = SpellChecker(dict_file, 2, 10)

   sc.check(text)
