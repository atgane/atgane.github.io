# Patch for Ruby 3.2+ compatibility: String#tainted? was removed in Ruby 3.2
# but liquid-4.0.3 still references it.
unless "".respond_to?(:tainted?)
  class String
    def tainted?
      false
    end
  end
end
